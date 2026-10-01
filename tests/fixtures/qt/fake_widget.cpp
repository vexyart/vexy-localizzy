#include "fake_widget.h"

// A QObject-derived class WITHOUT Q_OBJECT but using tr() -> QT-CTX-001.
class BadDialog : public QDialog {
public:
    BadDialog(QWidget *parent) : QDialog(parent) {
        setWindowTitle(tr("Glyph Editor"));        // marked literal
        label->setText("Hardcoded Label");          // QT-HARD-003
        button->setText(someVar);                    // hardcoded? no, not literal
        status->setText(tr(dynamicTitle));           // QT-TR-002 non-literal
        QString msg = tr("Kerning ").arg(a).arg(b);  // QT-ARG-006
        info->setText(tr("Pair ") + tr("value"));    // QT-CONCAT-007
    }
};

// A correctly-instrumented class with Q_OBJECT.
class GoodDialog : public QMainWindow {
    Q_OBJECT
public:
    GoodDialog() {
        setWindowTitle(tr("Font Window"));
        deprecated->setText(trUtf8("old"));          // QT-TRUTF8-011
    }
};
