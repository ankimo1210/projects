//
//  TitleView.swift
//  NeonThread
//

import SwiftUI

struct TitleView: View {
    let highScore: Int
    let onStart: () -> Void

    @AppStorage("isSoundEnabled") private var isSoundEnabled = true
    @AppStorage("isHapticsEnabled") private var isHapticsEnabled = true

    var body: some View {
        VStack(spacing: 48) {
            VStack(spacing: 16) {
                Text("NeonThread")
                    .font(.system(size: 44, weight: .heavy, design: .rounded))
                    .foregroundStyle(.cyan)
                    .shadow(color: .cyan, radius: 12)

                if highScore > 0 {
                    Text("BEST \(highScore)")
                        .font(.system(size: 18, weight: .bold, design: .rounded))
                        .foregroundStyle(.pink)
                        .shadow(color: .pink, radius: 8)
                }
            }

            Button(action: onStart) {
                Text("START")
                    .font(.system(size: 24, weight: .bold, design: .rounded))
                    .foregroundStyle(.black)
                    .padding(.horizontal, 48)
                    .padding(.vertical, 14)
                    .background(Capsule().fill(Color.cyan))
                    .shadow(color: .cyan, radius: 10)
            }

            HStack(spacing: 32) {
                settingToggle(
                    isOn: $isSoundEnabled,
                    onIcon: "speaker.wave.2.fill",
                    offIcon: "speaker.slash.fill"
                )
                settingToggle(
                    isOn: $isHapticsEnabled,
                    onIcon: "hand.tap.fill",
                    offIcon: "hand.tap"
                )
            }
        }
    }

    private func settingToggle(isOn: Binding<Bool>, onIcon: String, offIcon: String) -> some View {
        Button {
            isOn.wrappedValue.toggle()
            AudioService.shared.play(.button)
            HapticsService.shared.impact(.light)
        } label: {
            Image(systemName: isOn.wrappedValue ? onIcon : offIcon)
                .font(.system(size: 22))
                .foregroundStyle(isOn.wrappedValue ? .cyan : .gray)
                .frame(width: 52, height: 52)
                .overlay(
                    Circle().stroke(isOn.wrappedValue ? Color.cyan : Color.gray, lineWidth: 1.5)
                )
                .shadow(color: isOn.wrappedValue ? .cyan : .clear, radius: 6)
        }
    }
}

#Preview {
    ZStack {
        Color.black.ignoresSafeArea()
        TitleView(highScore: 128, onStart: {})
    }
}
