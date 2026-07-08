//
//  GameViewModel.swift
//  NeonThread
//

import Combine
import SpriteKit
import SwiftUI

enum GameState {
    case title
    case playing
    case gameOver
}

@MainActor
final class GameViewModel: ObservableObject {
    @Published var gameState: GameState = .title
    @Published var score = 0
    @Published var lives = 3
    @Published var coins = 0
    @Published var lastScore = 0
    @Published var lastCoins = 0
    @Published var highScore = UserDefaults.standard.integer(forKey: "highScore")
    @Published var isNewRecord = false

    private(set) var scene: GameScene?

    func startGame() {
        score = 0
        lives = 3
        coins = 0
        isNewRecord = false

        AudioService.shared.play(.start)
        HapticsService.shared.impact(.medium)
        AudioService.shared.startBGM()

        let scene = GameScene(size: UIScreen.main.bounds.size)
        scene.scaleMode = .resizeFill
        scene.onScoreChanged = { [weak self] score in
            Task { @MainActor in self?.score = score }
        }
        scene.onLivesChanged = { [weak self] lives in
            Task { @MainActor in self?.lives = lives }
        }
        scene.onCoinsChanged = { [weak self] coins in
            Task { @MainActor in self?.coins = coins }
        }
        scene.onGameOver = { [weak self] finalScore in
            Task { @MainActor in self?.finishGame(finalScore: finalScore) }
        }
        self.scene = scene
        gameState = .playing
    }

    private func finishGame(finalScore: Int) {
        lastScore = finalScore
        lastCoins = coins

        let defaults = UserDefaults.standard
        if finalScore > highScore {
            highScore = finalScore
            isNewRecord = true
            defaults.set(finalScore, forKey: "highScore")
        }
        defaults.set(defaults.integer(forKey: "totalCoins") + coins, forKey: "totalCoins")

        scene = nil
        gameState = .gameOver
    }

    func returnToTitle() {
        AudioService.shared.play(.button)
        HapticsService.shared.impact(.light)
        scene = nil
        gameState = .title
    }
}
