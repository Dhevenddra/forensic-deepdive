// JAX-RS resource (DEC-062) — class @Path + verb/@Path methods.
@Path("/owners")
public class OwnerResource {
    @GET
    public Object list() {
        return null;
    }

    @GET
    @Path("/{id}")
    public Object get() {
        return null;
    }

    @POST
    public void create() {}
}
