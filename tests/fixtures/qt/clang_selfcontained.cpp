// Self-contained Qt stand-ins so libclang parses cleanly without Qt headers.
#define Q_OBJECT

class QString {
public:
    QString(const char *) {}
};

class QObject {
public:
    static QString tr(const char *text) { return QString(text); }
};

class QDialog : public QObject {};

// Derives from QDialog, calls tr(), but lacks Q_OBJECT -> QT-CTX-001.
class BadDialog : public QDialog {
public:
    void build(const char *dynamicTitle) {
        tr("Literal title");
        tr(dynamicTitle);  // non-literal -> QT-TR-002
    }
};

// Correctly instrumented: Q_OBJECT present, literal tr() only.
class GoodDialog : public QDialog {
    Q_OBJECT
public:
    void build() { tr("Fine"); }
};
