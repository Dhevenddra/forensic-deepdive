// DEC-059 — a Spring controller injecting an interface with two impls
// (AMBIGUOUS-all) and a concrete repository (the single-impl → INFERRED case via
// OwnerRepository → OwnerRepositoryImpl), plus a JPA entity → table.
@RestController
public class OwnerController {
    @Autowired
    private Notifier notifier;

    @Autowired
    private OwnerRepository owners;
}
