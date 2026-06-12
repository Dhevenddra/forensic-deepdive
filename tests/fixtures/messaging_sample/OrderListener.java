// A Spring @KafkaListener — a subscriber (provider) on topic::orders, joining a
// Python producer.send("orders") cross-language.
public class OrderListener {
    @KafkaListener(topics = "orders")
    public void onOrder(String message) {
    }
}
