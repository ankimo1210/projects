//
//  ContentView.swift
//  NeonThread
//

import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = GameViewModel()

    var body: some View {
        ZStack {
            Color(red: 0.02, green: 0.02, blue: 0.08)
                .ignoresSafeArea()

            switch viewModel.gameState {
            case .title:
                TitleView(
                    highScore: viewModel.highScore,
                    onStart: { viewModel.startGame() }
                )
            case .playing:
                GameView(viewModel: viewModel)
            case .gameOver:
                GameOverView(
                    score: viewModel.lastScore,
                    highScore: viewModel.highScore,
                    coins: viewModel.lastCoins,
                    isNewRecord: viewModel.isNewRecord,
                    onRetry: { viewModel.startGame() },
                    onTitle: { viewModel.returnToTitle() }
                )
            }
        }
        .preferredColorScheme(.dark)
        .statusBarHidden()
    }
}

#Preview {
    ContentView()
}
