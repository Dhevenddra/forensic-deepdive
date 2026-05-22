/// A tiny greeting library used by the static-analysis fixtures.
class Greeter {
  final String who;

  Greeter(this.who);

  String greet() => formatMessage(who);
}

String formatMessage(String name) {
  return 'hello, $name';
}
