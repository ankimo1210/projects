import CoreWLAN
import Foundation

let name = CommandLine.arguments.dropFirst().first
let client = CWWiFiClient.shared()
let interface = name != nil ? client.interface(withName: name!) : client.interface()
var values: [String: Any] = ["available": false]
if let wifi = interface, wifi.powerOn(), let channel = wifi.wlanChannel() {
    let widths: [CWChannelWidth: Int] = [
        .width20MHz: 20, .width40MHz: 40, .width80MHz: 80,
        .width160MHz: 160,
    ]
    values = ["available": true, "interface": wifi.interfaceName ?? "",
              "rssi_dbm": wifi.rssiValue(), "noise_dbm": wifi.noiseMeasurement(),
              "tx_mbps": wifi.transmitRate(), "channel": channel.channelNumber,
              "width_mhz": widths[channel.channelWidth] ?? 0]
}
// No scan, SSID, BSSID, MAC address, location permission or network changes.
let data = try JSONSerialization.data(withJSONObject: values, options: [.sortedKeys])
print(String(data: data, encoding: .utf8)!)
