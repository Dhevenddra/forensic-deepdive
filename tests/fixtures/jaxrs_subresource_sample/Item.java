package store;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;

// A sub-resource (no class @Path) reached only via BookStore.getItem(). Its @GET is a
// leaf route under the locator prefix; getTrack() is a *nested* locator → Track.
public class Item {

    @GET
    public Item read() {
        return this;
    }

    @Path("track/")
    public Track getTrack() {
        return new Track();
    }
}
