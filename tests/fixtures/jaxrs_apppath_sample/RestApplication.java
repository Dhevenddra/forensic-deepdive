package shop;

import jakarta.ws.rs.ApplicationPath;
import jakarta.ws.rs.core.Application;

// The JAX-RS Application subclass: @ApplicationPath sets the servlet mount path for the
// whole application, so every resource path is relative to "/api" (DEC-073).
@ApplicationPath("/api")
public class RestApplication extends Application {
}
