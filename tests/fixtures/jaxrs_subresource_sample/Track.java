package store;

import jakarta.ws.rs.GET;

// Nested sub-resource reached via Item.getTrack().
public class Track {

    @GET
    public Track read() {
        return this;
    }
}
