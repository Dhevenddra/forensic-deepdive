import 'api.dart';
import 'post.dart';

/// On-screen list of posts loaded from the API.
class FeedView {
  final Api api;
  List<Post> posts;

  FeedView(this.api) : posts = <Post>[];

  Future<void> refresh() async {
    posts = await fetchPosts(api);
  }
}
