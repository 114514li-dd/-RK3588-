#include "previewlabel.h"

#include <QPainter>
#include <QPaintEvent>
#include <QFontMetrics>

namespace {

struct ImageDrawMetrics {
    double scale;
    int offsetX;
    int offsetY;
    int drawW;
    int drawH;
};

ImageDrawMetrics computeDrawMetrics(const QPixmap &pix, int widgetW, int widgetH)
{
    ImageDrawMetrics metrics;
    const double scaleX = static_cast<double>(widgetW) / static_cast<double>(pix.width());
    const double scaleY = static_cast<double>(widgetH) / static_cast<double>(pix.height());
    metrics.scale = qMin(scaleX, scaleY);
    metrics.drawW = static_cast<int>(pix.width() * metrics.scale);
    metrics.drawH = static_cast<int>(pix.height() * metrics.scale);
    metrics.offsetX = (widgetW - metrics.drawW) / 2;
    metrics.offsetY = (widgetH - metrics.drawH) / 2;
    return metrics;
}

QRect mapBboxToWidget(const QRect &bbox, const ImageDrawMetrics &metrics)
{
    const int x = metrics.offsetX + static_cast<int>(bbox.x() * metrics.scale);
    const int y = metrics.offsetY + static_cast<int>(bbox.y() * metrics.scale);
    const int w = qMax(4, static_cast<int>(bbox.width() * metrics.scale));
    const int h = qMax(4, static_cast<int>(bbox.height() * metrics.scale));
    return QRect(x, y, w, h);
}

} // namespace

PreviewLabel::PreviewLabel(QWidget *parent)
    : QLabel(parent)
{
    setAlignment(Qt::AlignCenter);
    setMinimumSize(480, 360);
    setScaledContents(false);
}

void PreviewLabel::setDetections(const QVector<HerbDetectItem> &items)
{
    m_detections = items;
    update();
}

void PreviewLabel::clearDetections()
{
    m_detections.clear();
    update();
}

void PreviewLabel::paintEvent(QPaintEvent *event)
{
    if (pixmap() == NULL || pixmap()->isNull()) {
        QLabel::paintEvent(event);
        return;
    }

    const QPixmap pix = *pixmap();
    const ImageDrawMetrics metrics = computeDrawMetrics(pix, width(), height());

    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing);
    painter.fillRect(rect(), palette().color(QPalette::Window));

    painter.drawPixmap(metrics.offsetX, metrics.offsetY, metrics.drawW, metrics.drawH, pix);

    if (m_detections.isEmpty()) {
        return;
    }

    QFont font = painter.font();
    font.setPointSize(10);
    font.setBold(true);
    painter.setFont(font);
    const QFontMetrics fm(font);

    const QPen boxPen(QColor(255, 60, 60), 3);
    painter.setBrush(Qt::NoBrush);

    for (int i = 0; i < m_detections.size(); ++i) {
        const HerbDetectItem &item = m_detections.at(i);
        if (!item.bbox.isValid()) {
            continue;
        }

        const QRect boxRect = mapBboxToWidget(item.bbox, metrics);
        painter.setPen(boxPen);
        painter.drawRect(boxRect);

        const QString label = QStringLiteral("%1 %2")
                                  .arg(item.name)
                                  .arg(QString::number(item.confidence, 'f', 2));
        const int labelW = fm.width(label) + 10;
        const int labelH = fm.height() + 4;
        int labelX = boxRect.x();
        int labelY = boxRect.y() - labelH - 2;
        if (labelY < metrics.offsetY) {
            labelY = boxRect.y() + 2;
        }
        if (labelX + labelW > metrics.offsetX + metrics.drawW) {
            labelX = metrics.offsetX + metrics.drawW - labelW;
        }

        const QRect labelRect(labelX, labelY, labelW, labelH);
        painter.fillRect(labelRect, QColor(255, 60, 60));
        painter.setPen(Qt::white);
        painter.drawText(labelRect, Qt::AlignCenter, label);
    }
}
