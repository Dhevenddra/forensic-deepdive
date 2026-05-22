import 'greeter.dart';

void main() {
  final greeter = Greeter('world');
  print(greeter.greet());
  print(formatMessage('again'));
}
