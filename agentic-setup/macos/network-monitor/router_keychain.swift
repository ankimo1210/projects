import Foundation
import Security

// The password enters only through stdin and never leaves this helper in plaintext.
let service = "com.ankimo.network-router"
let account = "admin"
let query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrService as String: service,
    kSecAttrAccount as String: account,
    kSecUseAuthenticationUI as String: kSecUseAuthenticationUIFail,
]

func fail(_ reason: String) -> Never {
    FileHandle.standardError.write(Data((reason + "\n").utf8))
    exit(1)
}

func output(_ value: [String: Any]) {
    guard let data = try? JSONSerialization.data(withJSONObject: value) else { fail("encoding_failed") }
    print(String(decoding: data, as: UTF8.self))
}

func input() -> [String: Any] {
    let data = FileHandle.standardInput.readDataToEndOfFile()
    guard data.count < 16384,
          let value = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    else { fail("invalid_input") }
    return value
}

func der(_ tag: UInt8, _ data: Data) -> Data {
    var length = data.count
    var bytes: [UInt8] = []
    repeat { bytes.insert(UInt8(length & 255), at: 0); length >>= 8 } while length > 0
    let header: [UInt8] = data.count < 128 ? [tag, UInt8(data.count)] : [tag, 0x80 | UInt8(bytes.count)] + bytes
    return Data(header) + data
}

func integer(_ source: Data) -> Data {
    var data = source
    while data.count > 1 && data.first == 0 { data.removeFirst() }
    if let first = data.first, first & 0x80 != 0 { data.insert(0, at: 0) }
    return der(0x02, data)
}

let command = CommandLine.arguments.dropFirst().first ?? "status"
switch command {
case "status":
    var attributes = query
    attributes[kSecReturnAttributes as String] = true
    let status = SecItemCopyMatching(attributes as CFDictionary, nil)
    guard status == errSecSuccess || status == errSecItemNotFound else { fail("keychain_unavailable_\(status)") }
    output(["exists": status == errSecSuccess])
case "store":
    let value = input()
    guard value["username"] as? String == account,
          let password = value["password"] as? String, !password.isEmpty,
          password.utf8.count <= 512 else { fail("invalid_credential") }
    var attributes = query
    attributes.removeValue(forKey: kSecUseAuthenticationUI as String)
    attributes[kSecAttrLabel as String] = "Home router read-only monitoring"
    attributes[kSecValueData as String] = Data(password.utf8)
    let status = SecItemAdd(attributes as CFDictionary, nil)
    // Never overwrite an existing credential silently.
    guard status == errSecSuccess else { fail("keychain_store_failed_\(status)") }
    output(["stored": true])
case "payload":
    let value = input()
    guard let hex = value["modulus"] as? String, hex.count == 512,
          hex.allSatisfy({ $0.isHexDigit }),
          let exponent = value["exponent"] as? String, exponent == "65537"
    else { fail("invalid_public_key") }
    var modulus = Data()
    var index = hex.startIndex
    while index < hex.endIndex {
        let end = hex.index(index, offsetBy: 2)
        guard let byte = UInt8(hex[index..<end], radix: 16) else { fail("invalid_public_key") }
        modulus.append(byte)
        index = end
    }
    let publicDER = der(0x30, integer(modulus) + integer(Data([1, 0, 1])))
    let attributes: [String: Any] = [kSecAttrKeyType as String: kSecAttrKeyTypeRSA,
                                    kSecAttrKeyClass as String: kSecAttrKeyClassPublic]
    var error: Unmanaged<CFError>?
    guard let key = SecKeyCreateWithData(publicDER as CFData, attributes as CFDictionary, &error)
    else { fail("public_key_failed") }
    var secretQuery = query
    secretQuery[kSecReturnData as String] = true
    var item: CFTypeRef?
    let status = SecItemCopyMatching(secretQuery as CFDictionary, &item)
    guard status == errSecSuccess, let secret = item as? Data,
          let password = String(data: secret, encoding: .utf8) else { fail("credential_unavailable_\(status)") }
    let allowed = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.!~*'()")
    guard let encoded = password.addingPercentEncoding(withAllowedCharacters: allowed),
          let cipher = SecKeyCreateEncryptedData(key, .rsaEncryptionPKCS1,
                                                Data(("airstation_pass=" + encoded).utf8) as CFData, &error)
    else { fail("encryption_failed") }
    let base64 = (cipher as Data).base64EncodedString()
    let lines = stride(from: 0, to: base64.count, by: 64).map { offset -> String in
        let start = base64.index(base64.startIndex, offsetBy: offset)
        let end = base64.index(start, offsetBy: min(64, base64.count - offset))
        return String(base64[start..<end])
    }
    output(["username": account, "encrypted": lines.joined(separator: "\n")])
default: fail("unknown_command")
}
