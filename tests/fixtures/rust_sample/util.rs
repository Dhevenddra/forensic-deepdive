// A small helper module imported by greeter.rs (crate-internal use).

pub fn shout(text: &str) -> String {
    format!("{}!", text)
}
