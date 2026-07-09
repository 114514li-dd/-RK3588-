#ifndef HERBDETECTION_H
#define HERBDETECTION_H

#include <QImage>
#include <QRect>
#include <QString>
#include <QVector>

struct HerbDetectItem
{
    QString name;
    double confidence;
    QRect bbox;

    HerbDetectItem()
        : confidence(0.0)
    {
    }

    bool isGouqi() const;
};

struct HerbDetectResult
{
    bool success;
    QString errorMessage;
    QVector<HerbDetectItem> items;

    HerbDetectItem bestGouqi() const;
};

class HerbDetector
{
public:
    static HerbDetectResult detect(const QImage &image, const QString &imagePath);
};

#endif // HERBDETECTION_H
