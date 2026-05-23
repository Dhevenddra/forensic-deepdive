import 'post.dart';

/// HTTP client for the blog API.
class Api {
  final String baseUrl;

  const Api(this.baseUrl);
}

Future<List<Post>> fetchPosts(Api api) async {
  return <Post>[];
}
