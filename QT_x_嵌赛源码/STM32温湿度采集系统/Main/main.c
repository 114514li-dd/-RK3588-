#include <stdio.h>
#include "stm32f10x.h"
#include "bsp_delay.h"
#include "bsp_key.h"
#include "bsp_oled.h"
#include "bsp_dht11.h"
#include "bsp_Alarm.h"
#include "bsp_led.h"
#include "bsp_usart.h"
#include "esp8266.h"
#include "onenet.h"

DHT11_Data_TypeDef DHT11_Data;
char oled_Temp[16],oled_TempThr[16];
char oled_Hum[16],oled_HumThr[16];
uint8_t key_value = 0;
uint8_t Temp_Thr = 30;
uint8_t Hum_Thr = 60;
char PUBLIS_BUF[256];    
const char devPubTopic[] = "$sys/006jQmKSbY/Test/thing/property/post";   //主题的订阅
const char *devSubTopic[] = {"$sys/006jQmKSbY/Test/thing/property/set"};
unsigned char * dataPtr = NULL;
uint16_t TimeCount = 0;
uint8_t Alarm_flag = 0;
typedef enum{
		
	MAIN_MENU, //主菜单界面
	TEMP_SET,  //温度阈值设置界面
	HUM_SET,   //湿度阈值设置界面
}DisplayState;


DisplayState currentState = MAIN_MENU;

/*
---------------------------------------------------------------------------------------------------------
*	函 数 名: Bsp_init
*	功能说明: 各个模块的初始化函数(串口、OELD、按键等)
*	参    数：无
*	返 回 值: 无
---------------------------------------------------------------------------------------------------------
*/
void Bsp_init()
{
		DHT11_Init();
		OLED_Init();
		Delay_Init();
		Key_Init();
		Alarm_Init();
		Usart_Init();
		LED_Init();
}
/*
---------------------------------------------------------------------------------------------------------
*	函 数 名:  Oled_Show
*	功能说明: OLED显示屏显示温湿度数据信息
*	参    数：无
*	返 回 值: 无
---------------------------------------------------------------------------------------------------------
*/

void Oled_show()
{
		 OLED_ShowCH(5,0,"温湿度采集系统");
	
		 if(DHT11_Read_TempAndHumidity(&DHT11_Data) == 1)
		 {
			 sprintf(oled_Temp,"Temp:%d.%d",DHT11_Data.temp_int,DHT11_Data.temp_deci);
			 OLED_ShowCH(20,3,(char*)oled_Temp);
			 sprintf(oled_Hum,"Hum:%d%%",DHT11_Data.humi_int);
			 OLED_ShowCH(20,5,(char*)oled_Hum);			
		 }
		
}
/*
---------------------------------------------------------------------------------------------------------
*	函 数 名:  Oled_Show1
*	功能说明: OLED显示屏显示设置温度阈值界面
*	参    数：无
*	返 回 值: 无
---------------------------------------------------------------------------------------------------------
*/
void Oled_show1()
{
		OLED_ShowCH(30,0,"温度阈值");
		if(key_value == 2)
		{
				if(Temp_Thr < 100)
				{
					Temp_Thr++;
				}
		}
		else if(key_value == 3)
		{
				if(Temp_Thr > 0)
				{
					Temp_Thr--;
				}			
		}
		sprintf(oled_TempThr,"Temp:%d",Temp_Thr);
		OLED_ShowCH(30,4,(u8*)oled_TempThr);		
}
/*
---------------------------------------------------------------------------------------------------------
*	函 数 名:  Oled_Show2
*	功能说明: OLED显示屏显示设置湿度阈值界面
*	参    数：无
*	返 回 值: 无
---------------------------------------------------------------------------------------------------------
*/
void Oled_show2()
{
		OLED_ShowCH(30,0,"湿度阈值");
		if(key_value == 2)
		{
				if(Hum_Thr < 100)
				{
					Hum_Thr++;
				}
		}
		else if(key_value == 3)
		{
				if(Hum_Thr > 0)
				{
					Hum_Thr--;
				}			
		}
		sprintf(oled_HumThr,"Hum:%d",Hum_Thr);
		OLED_ShowCH(30,4,(u8*)oled_HumThr);		
}

/*
---------------------------------------------------------------------------------------------------------
*	函 数 名: Oled_Switch()
*	功能说明: OLED界面切换函数
*	参    数：无
*	返 回 值: 无
---------------------------------------------------------------------------------------------------------
*/
void Oled_Switch()
{
	 key_value = Key_Scan(0);
	 if(key_value == 1)
	 {
			currentState = (currentState + 1) % 3;	
			OLED_Clear();
	 }

	 switch(currentState)
	 {
			case MAIN_MENU:
					Oled_show();
					break;
			case TEMP_SET:
					Oled_show1();
					break;
			case HUM_SET:	
					Oled_show2();
					break; 
	 }
}

void JsonValue()
{
	uint8_t Temp = DHT11_Data.temp_int;
	uint8_t Hum = DHT11_Data.humi_int;
	
	memset(PUBLIS_BUF, 0, sizeof(PUBLIS_BUF));
	
	sprintf(PUBLIS_BUF,"{\"id\":\"123\",\"params\":{\"Temp\":{\"value\":%d},\"Hum\":{\"value\":%d} }}",//定义一下
					DHT11_Data.temp_int,DHT11_Data.humi_int);	
}

void Alarm_Statue()
{
	if(Alarm_flag == 1)
	{
		if(DHT11_Data.temp_int > Temp_Thr || DHT11_Data.humi_int > Hum_Thr)
		{
				Alarm_ON();
		}
		else
		{
				Alarm_OFF();
		}
	}
	else 
	{
		Alarm_OFF();
	}
}


int main()
{
		Bsp_init();
		OLED_ShowCH(20,3,"网络连接中...");	
		ESP8266_Init();
		while(OneNet_DevLink())//连接Onenet平台,如果失败等待500ms继续尝试。
		{
			DelayXms(500);
		}
		OLED_Clear();		
		OLED_ShowCH(20,3,"连接成功");
		DelayXms(3000);
		OLED_Clear();
		/*订阅主题*/
		OneNet_Subscribe(devSubTopic,1);
		while(1)
		{
				Oled_Switch();
				Alarm_Statue();
			
			  if(++TimeCount >= 100)//延迟   500ms上传一次
				{
					JsonValue();
					OneNet_Publish(devPubTopic, PUBLIS_BUF);
					ESP8266_Clear();
					TimeCount = 0;
					
				}					
				      //DelayXms(5);	
				dataPtr =  ESP8266_GetIPD(2);
				if(dataPtr != NULL)
				{
					OneNet_RevPro(dataPtr);
				}
			
		}
}





