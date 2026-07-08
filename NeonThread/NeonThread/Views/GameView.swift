//
//  GameView.swift
//  NeonThread
//

import SpriteKit
import SwiftUI

struct GameView: View {
    @ObservedObject var viewModel: GameViewModel

    var body: some View {
        ZStack {
            if let scene = viewModel.scene {
                SpriteView(scene: scene)
                    .ignoresSafeArea()
            }

            VStack {
                HStack {
                    HStack(spacing: 6) {
                        Image(systemName: "heart.fill")
                            .symbolEffect(.bounce, options: .speed(1.4), value: viewModel.lives)
                        Text("\(viewModel.lives)")
                    }
                    .font(.system(size: 20, weight: .bold, design: .rounded))
                    .foregroundStyle(.pink)
                    .shadow(color: .pink, radius: 6)
                    Spacer()
                    HStack(spacing: 6) {
                        Circle()
                            .fill(Color(red: 0.75, green: 1.0, blue: 0.2))
                            .frame(width: 12, height: 12)
                        Text("\(viewModel.coins)")
                    }
                    .font(.system(size: 20, weight: .bold, design: .rounded))
                    .foregroundStyle(Color(red: 0.75, green: 1.0, blue: 0.2))
                    .shadow(color: Color(red: 0.75, green: 1.0, blue: 0.2), radius: 6)
                    Spacer()
                    Text("\(viewModel.score)")
                        .font(.system(size: 28, weight: .heavy, design: .rounded))
                        .foregroundStyle(.cyan)
                        .shadow(color: .cyan, radius: 6)
                }
                .padding(.horizontal, 20)
                Spacer()
            }
            .allowsHitTesting(false)
        }
    }
}
