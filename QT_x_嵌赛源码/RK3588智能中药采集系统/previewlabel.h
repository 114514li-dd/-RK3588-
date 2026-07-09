#ifndef PREVIEWLABEL_H
#define PREVIEWLABEL_H

#include "herbdetection.h"

#include <QLabel>
#include <QVector>

class PreviewLabel : public QLabel
{
    Q_OBJECT

public:
    explicit PreviewLabel(QWidget *parent = 0);

    void setDetections(const QVector<HerbDetectItem> &items);
    void clearDetections();

protected:
    void paintEvent(QPaintEvent *event) override;

private:
    QVector<HerbDetectItem> m_detections;
};

#endif // PREVIEWLABEL_H
