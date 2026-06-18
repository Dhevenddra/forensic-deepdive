package shop;

import jakarta.ws.rs.GET;

// An interface return type for the widget() locator. It has no concrete class of this
// name, so the locator resolves via its single implementer (DEC-073 → INFERRED).
public interface WidgetService {
    @GET
    String read();
}
