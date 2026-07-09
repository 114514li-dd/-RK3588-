#include <stdio.h>
int main()
	{
	int input = 0;
	printf("hello\n");
	printf("选择好坏（1/0）");
	scanf_s("%d", &input);//
	if (input == 1)
	{
		printf("你好\n");
	}
	else
	{
		printf("我你跌\n");
	}

		return 0;
	}