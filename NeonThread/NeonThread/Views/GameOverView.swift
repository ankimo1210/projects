//
//  GameOverView.swift
//  NeonThread
//

import SwiftUI

struct GameOverView: View {
    let score: Int
    let highScore: Int
    let coins: Int
    let isNewRecord: Bool
    let onRetry: () -> Void
    let onTitle: () -> Void

    private let lime = Color(red: 0.75, green: 1.0, blue: 0.2)

    var body: some View {
        VStack(spacing: 36) {
            Text("GAME OVER")
                .font(.system(size: 36, weight: .heavy, design: .rounded))
                .foregroundStyle(.pink)
                .shadow(color: .pink, radius: 12)

            VStack(spacing: 8) {
                if isNewRecord {
                    Text("NEW RECORD!")
                        .font(.system(size: 18, weight: .heavy, design: .rounded))
                        .foregroundStyle(.yellow)
                        .shadow(color: .yellow, radius: 8)
                }
                Text("SCORE")
                    .font(.system(size: 16, weight: .semibold, design: .rounded))
                    .foregroundStyle(.gray)
                Text("\(score)")
                    .font(.system(size: 52, weight: .heavy, design: .rounded))
                    .foregroundStyle(.cyan)
                    .shadow(color: .cyan, radius: 8)

                HStack(spacing: 20) {
                    Text("BEST \(highScore)")
                        .foregroundStyle(.pink)
                        .shadow(color: .pink, radius: 6)
                    HStack(spacing: 6) {
                        Circle().fill(lime).frame(width: 10, height: 10)
                        Text("\(coins)")
                    }
                    .foregroundStyle(lime)
                    .shadow(color: lime, radius: 6)
                }
                .font(.system(size: 16, weight: .bold, design: .rounded))
                .padding(.top, 4)
            }

            VStack(spacing: 16) {
                Button(action: onRetry) {
                    Text("RETRY")
                        .font(.system(size: 22, weight: .bold, design: .rounded))
                        .foregroundStyle(.black)
                        .padding(.horizontal, 44)
                        .padding(.vertical, 12)
                        .background(Capsule().fill(Color.cyan))
                        .shadow(color: .cyan, radius: 10)
                }
                Button(action: onTitle) {
                    Text("TITLE")
                        .font(.system(size: 18, weight: .semibold, design: .rounded))
                        .foregroundStyle(.cyan)
                        .padding(.horizontal, 32)
                        .padding(.vertical, 10)
                        .overlay(Capsule().stroke(Color.cyan, lineWidth: 2))
                }
            }
        }
    }
}

#Preview {
    ZStack {
        Color.black.ignoresSafeArea()
        GameOverView(score: 128, highScore: 128, coins: 7, isNewRecord: true, onRetry: {}, onTitle: {})
    }
}
