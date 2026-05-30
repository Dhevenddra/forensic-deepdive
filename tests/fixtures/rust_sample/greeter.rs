use crate::util::shout;
use std::fmt;

/// A trait the Greeter implements.
pub trait Greet {
    fn greet(&self) -> String;
}

pub struct Greeter {
    name: String,
}

impl Greeter {
    pub fn new(name: String) -> Self {
        Greeter { name }
    }

    fn render(&self) -> String {
        shout(&self.name)
    }
}

impl Greet for Greeter {
    fn greet(&self) -> String {
        self.render()
    }
}

pub enum Mood {
    Happy,
    Grumpy,
}

mod inner {
    pub fn nested() {}
}

fn main() {
    let g = Greeter::new(String::from("world"));
    g.greet();
}
