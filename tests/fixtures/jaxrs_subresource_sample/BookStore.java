package store;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;

// Root resource. getItem() is a sub-resource locator (@Path, no verb, returns Item);
// getAny() returns Object → unresolvable → emitted as an unmatched locator (no guess).
@Path("/store")
public class BookStore {

    @Path("items/{id}/")
    public Item getItem(String id) {
        return new Item();
    }

    @Path("anything/")
    public Object getAny() {
        return new Object();
    }
}
