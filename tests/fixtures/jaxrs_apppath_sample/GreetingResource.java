package shop;

import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import java.util.List;

// Resource under the "/api" app prefix. Class-level @Produces is the per-method default;
// a method-level @Produces/@Consumes overrides it (DEC-073 content negotiation). widget()
// is an interface-return sub-resource locator (resolved via implements → INFERRED).
@Path("/greetings")
@Produces(MediaType.APPLICATION_JSON)
public class GreetingResource {

    @GET
    public List<String> list() {
        return List.of();
    }

    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    public String create(String body) {
        return body;
    }

    @GET
    @Path("{id}")
    @Produces({MediaType.APPLICATION_JSON, MediaType.APPLICATION_XML})
    public String get(String id) {
        return id;
    }

    @Path("widget")
    public WidgetService widget() {
        return new WidgetServiceImpl();
    }
}
