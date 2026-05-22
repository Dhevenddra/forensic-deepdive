import Foundation

protocol Named {
    var name: String { get }
}

class Greeter: Named {
    let name: String

    init(name: String) {
        self.name = name
    }

    func greet() -> String {
        return formatMessage(name)
    }
}

func formatMessage(_ name: String) -> String {
    return "hello, \(name)"
}
