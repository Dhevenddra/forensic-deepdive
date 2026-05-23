import 'api.dart';
import 'feed_view.dart';

void main() {
  final api = Api('https://example.com');
  final view = FeedView(api);
  print(view);
}
