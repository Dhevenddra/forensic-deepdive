package shop;

import jakarta.ws.rs.GET;

// The single intra-repo implementer of WidgetService — the locator's INFERRED target.
// Its @GET method is the leaf route under "/api/greetings/widget".
public class WidgetServiceImpl implements WidgetService {

    @GET
    public String read() {
        return "widget";
    }
}
