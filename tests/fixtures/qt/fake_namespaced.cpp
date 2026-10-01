#include <QString>

// A class inside a namespace using Q_DECLARE_TR_FUNCTIONS -> QT-NS-004.
namespace app {

class Exporter {
    Q_DECLARE_TR_FUNCTIONS(Exporter)
public:
    QString title() { return tr("Export"); }
};

}  // namespace app

// QT_TR_NOOP at file scope (no class context) -> QT-NOOP-008.
static const char *kModeName = QT_TR_NOOP("Outline mode");

// A qualified Q_DECLARE_TR_FUNCTIONS context -> QT-NS-004 (namespaced name).
class Other {
    Q_DECLARE_TR_FUNCTIONS(ns::Other)
};
