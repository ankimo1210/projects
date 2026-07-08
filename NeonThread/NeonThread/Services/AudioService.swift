//
//  AudioService.swift
//  NeonThread
//

import AVFoundation

@MainActor
final class AudioService {
    static let shared = AudioService()

    enum Effect: String, CaseIterable {
        case button = "sfx_button"
        case start = "sfx_start"
        case hit = "sfx_hit"
        case coin = "sfx_coin"
        case gameOver = "sfx_gameover"
    }

    private var effectPlayers: [Effect: [AVAudioPlayer]] = [:]
    private var bgmPlayer: AVAudioPlayer?
    private var pendingBGMStop: DispatchWorkItem?

    private var isSoundEnabled: Bool {
        UserDefaults.standard.object(forKey: "isSoundEnabled") as? Bool ?? true
    }

    private init() {
        // .ambient: respect the silent switch and mix with other apps' audio.
        try? AVAudioSession.sharedInstance().setCategory(.ambient)
        try? AVAudioSession.sharedInstance().setActive(true)

        for effect in Effect.allCases {
            guard let url = Bundle.main.url(forResource: effect.rawValue, withExtension: "caf") else {
                print("AudioService: missing asset \(effect.rawValue).caf")
                continue
            }
            let pool = (0..<2).compactMap { _ in try? AVAudioPlayer(contentsOf: url) }
            pool.forEach { $0.prepareToPlay() }
            effectPlayers[effect] = pool
        }
    }

    func play(_ effect: Effect) {
        guard isSoundEnabled, let pool = effectPlayers[effect], !pool.isEmpty else { return }
        let player = pool.first(where: { !$0.isPlaying }) ?? pool[0]
        player.currentTime = 0
        player.volume = 0.9
        player.play()
    }

    func startBGM() {
        guard isSoundEnabled else { return }
        pendingBGMStop?.cancel()
        pendingBGMStop = nil

        if bgmPlayer == nil {
            guard let url = Bundle.main.url(forResource: "bgm_loop", withExtension: "caf") else {
                print("AudioService: missing asset bgm_loop.caf")
                return
            }
            bgmPlayer = try? AVAudioPlayer(contentsOf: url)
            bgmPlayer?.numberOfLoops = -1
        }
        guard let bgm = bgmPlayer else { return }
        bgm.stop()
        bgm.currentTime = 0
        bgm.volume = 0
        bgm.play()
        bgm.setVolume(0.45, fadeDuration: 0.6)
    }

    func stopBGM(fadeOut: TimeInterval = 0.6) {
        guard let bgm = bgmPlayer, bgm.isPlaying else { return }
        bgm.setVolume(0, fadeDuration: fadeOut)
        let stop = DispatchWorkItem { [weak bgm] in bgm?.stop() }
        pendingBGMStop = stop
        DispatchQueue.main.asyncAfter(deadline: .now() + fadeOut + 0.05, execute: stop)
    }
}
