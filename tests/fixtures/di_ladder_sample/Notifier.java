// DEC-059 — an interface with TWO impls → the Spring NoUniqueBeanDefinition
// case: injecting the interface resolves to AMBIGUOUS-all (both impls).
public interface Notifier {
    void send(String msg);
}
