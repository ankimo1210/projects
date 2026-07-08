//
//  GameScene.swift
//  NeonThread
//

import SpriteKit
import UIKit

enum PhysicsCategory {
    static let player: UInt32 = 1 << 0
    static let obstacle: UInt32 = 1 << 1
    static let coin: UInt32 = 1 << 2
    static let worldBounds: UInt32 = 1 << 3
}

final class GameScene: SKScene, SKPhysicsContactDelegate {

    // MARK: - Callbacks to SwiftUI

    var onScoreChanged: ((Int) -> Void)?
    var onLivesChanged: ((Int) -> Void)?
    var onCoinsChanged: ((Int) -> Void)?
    var onGameOver: ((Int) -> Void)?

    // MARK: - Tuning (initial values, to be balanced later)

    private let playerRadius: CGFloat = 12
    private let playerXRatio: CGFloat = 0.3
    private let riseAcceleration: CGFloat = 2200
    private let fallAcceleration: CGFloat = 1800
    private let maxRiseSpeed: CGFloat = 520
    private let maxFallSpeed: CGFloat = 640
    private let pointsPerPoint: CGFloat = 0.1   // score per scrolled point
    private let wallWidth: CGFloat = 56
    private let gapEdgeMargin: CGFloat = 90
    private let invincibleDuration: TimeInterval = 1.2
    private let coinRadius: CGFloat = 9
    private let coinChance: CGFloat = 0.75
    private let coinBonus = 5

    // Difficulty ramp: everything scales with scrolled distance, capped.
    private let baseScrollSpeed: CGFloat = 180
    private let maxScrollSpeed: CGFloat = 320
    private let speedRamp: CGFloat = 0.02           // +pt/s per scrolled point
    private let baseGapHeight: CGFloat = 190
    private let minGapHeight: CGFloat = 140
    private let gapRamp: CGFloat = 0.008
    private let baseSpawnInterval: TimeInterval = 1.7
    private let minSpawnInterval: TimeInterval = 1.05
    private let spawnRamp: TimeInterval = 0.0002
    /// Distances at which obstacle phases 2-4 unlock (spec: 序盤/中盤/後半/終盤).
    private let phaseDistances: [CGFloat] = [400, 1000, 1800]

    private var scrollSpeed: CGFloat {
        min(maxScrollSpeed, baseScrollSpeed + distance * speedRamp)
    }
    private var gapHeight: CGFloat {
        max(minGapHeight, baseGapHeight - distance * gapRamp)
    }
    private var spawnInterval: TimeInterval {
        max(minSpawnInterval, baseSpawnInterval - TimeInterval(distance) * spawnRamp)
    }
    private var currentPhase: Int {
        phaseDistances.filter { distance >= $0 }.count
    }

    // MARK: - Nodes

    private var player: SKShapeNode!
    private let obstacleLayer = SKNode()
    private let cameraNode = SKCameraNode()
    private var flashNode: SKSpriteNode!
    private lazy var particleTexture: SKTexture = Self.makeParticleTexture()

    // MARK: - Run state

    private var isThrusting = false
    private var verticalVelocity: CGFloat = 0
    private var lastUpdateTime: TimeInterval = 0
    private var spawnTimer: TimeInterval = 0
    private var distance: CGFloat = 0
    private var score = 0
    private var bonusScore = 0
    private var coins = 0
    private var lives = 3
    private var isInvincible = false
    private var isGameOver = false

    // MARK: - Setup

    override func didMove(to view: SKView) {
        backgroundColor = SKColor(red: 0.02, green: 0.02, blue: 0.08, alpha: 1)
        physicsWorld.gravity = .zero
        physicsWorld.contactDelegate = self
        addChild(obstacleLayer)
        setupCamera()
        setupPlayer()
    }

    private func setupCamera() {
        cameraNode.position = CGPoint(x: size.width / 2, y: size.height / 2)
        addChild(cameraNode)
        camera = cameraNode

        // Full-screen flash overlay; child of the camera so it follows shakes.
        let flash = SKSpriteNode(
            color: .white,
            size: CGSize(width: size.width + 60, height: size.height + 60)
        )
        flash.alpha = 0
        flash.zPosition = 90
        flash.blendMode = .add
        cameraNode.addChild(flash)
        flashNode = flash
    }

    private func setupPlayer() {
        let node = SKShapeNode(circleOfRadius: playerRadius)
        node.fillColor = SKColor.cyan
        node.strokeColor = SKColor.cyan
        node.glowWidth = 8
        node.position = CGPoint(x: size.width * playerXRatio, y: size.height * 0.5)
        node.zPosition = 10

        let body = SKPhysicsBody(circleOfRadius: playerRadius)
        body.isDynamic = true
        body.affectedByGravity = false
        body.allowsRotation = false
        body.categoryBitMask = PhysicsCategory.player
        body.contactTestBitMask = PhysicsCategory.obstacle | PhysicsCategory.coin
        body.collisionBitMask = 0
        node.physicsBody = body

        if let trail = makeTrailEmitter() {
            trail.targetNode = self
            trail.position = CGPoint(x: -playerRadius, y: 0)
            node.addChild(trail)
        }

        addChild(node)
        player = node
    }

    private static func makeParticleTexture() -> SKTexture {
        let renderer = UIGraphicsImageRenderer(size: CGSize(width: 16, height: 16))
        let image = renderer.image { context in
            UIColor.white.setFill()
            context.cgContext.fillEllipse(in: CGRect(x: 0, y: 0, width: 16, height: 16))
        }
        return SKTexture(image: image)
    }

    private func makeTrailEmitter() -> SKEmitterNode? {
        let emitter = SKEmitterNode()
        emitter.particleTexture = particleTexture
        emitter.particleBirthRate = 60
        emitter.particleLifetime = 0.5
        emitter.particleAlpha = 0.7
        emitter.particleAlphaSpeed = -1.4
        emitter.particleScale = 0.5
        emitter.particleScaleSpeed = -0.9
        emitter.particleSpeed = 30
        emitter.emissionAngle = .pi
        emitter.particleColor = SKColor.cyan
        emitter.particleColorBlendFactor = 1
        emitter.particleBlendMode = .add
        return emitter
    }

    // MARK: - Input

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        isThrusting = true
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        isThrusting = false
    }

    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {
        isThrusting = false
    }

    // MARK: - Game loop

    override func update(_ currentTime: TimeInterval) {
        guard !isGameOver else { return }

        let dt: CGFloat
        if lastUpdateTime == 0 {
            dt = 0
        } else {
            dt = CGFloat(min(currentTime - lastUpdateTime, 1.0 / 30.0))
        }
        lastUpdateTime = currentTime
        guard dt > 0 else { return }

        movePlayer(dt: dt)
        moveObstacles(dt: dt)
        spawnIfNeeded(dt: dt)
        updateScore(dt: dt)
    }

    private func movePlayer(dt: CGFloat) {
        let accel = isThrusting ? riseAcceleration : -fallAcceleration
        verticalVelocity += accel * dt
        verticalVelocity = min(max(verticalVelocity, -maxFallSpeed), maxRiseSpeed)

        var y = player.position.y + verticalVelocity * dt
        let floorY = playerRadius + 4
        let ceilingY = size.height - playerRadius - 4
        if y <= floorY {
            y = floorY
            verticalVelocity = 0
        } else if y >= ceilingY {
            y = ceilingY
            verticalVelocity = 0
        }
        player.position.y = y
    }

    private func moveObstacles(dt: CGFloat) {
        let dx = scrollSpeed * dt
        for node in obstacleLayer.children {
            node.position.x -= dx
        }
        // -200: wide enough for a rotating bar's half-length plus glow.
        for node in obstacleLayer.children where node.position.x < -200 {
            node.removeFromParent()
        }
    }

    private func spawnIfNeeded(dt: CGFloat) {
        spawnTimer += TimeInterval(dt)
        guard spawnTimer >= spawnInterval else { return }
        spawnTimer = 0
        spawnObstacle()
    }

    /// Picks an obstacle type for the current phase (spec §3).
    private func spawnObstacle() {
        switch currentPhase {
        case 0:
            spawnWallPair(moving: false)
        case 1:
            spawnWallPair(moving: Bool.random())
        case 2:
            let roll = CGFloat.random(in: 0..<1)
            if roll < 0.35 {
                spawnWallPair(moving: true)
            } else if roll < 0.7 {
                spawnRotatingBar(offsetX: 0)
            } else {
                spawnWallPair(moving: false)
            }
        default:
            if Bool.random() {
                // Combo: moving pair plus a rotating bar halfway to the next spawn.
                spawnWallPair(moving: true)
                spawnRotatingBar(offsetX: scrollSpeed * spawnInterval / 2)
            } else {
                spawnWallPair(moving: Bool.random())
            }
        }
    }

    /// Phases 1-2: a top/bottom wall pair; when `moving`, the gap oscillates vertically.
    private func spawnWallPair(moving: Bool) {
        let gap = gapHeight
        let amplitude: CGFloat = moving ? .random(in: 50...90) : 0
        let minCenter = gapEdgeMargin + gap / 2 + amplitude
        let maxCenter = size.height - gapEdgeMargin - gap / 2 - amplitude
        guard maxCenter > minCenter else { return }
        let gapCenter = CGFloat.random(in: minCenter...maxCenter)
        let spawnX = size.width + wallWidth

        let pair = SKNode()
        pair.position = CGPoint(x: spawnX, y: 0)
        let bottomHeight = gapCenter - gap / 2
        if bottomHeight > 0 {
            pair.addChild(makeWall(bottom: 0, height: bottomHeight))
        }
        let topHeight = size.height - (gapCenter + gap / 2)
        if topHeight > 0 {
            pair.addChild(makeWall(bottom: gapCenter + gap / 2, height: topHeight))
        }

        if moving {
            let half = TimeInterval.random(in: 0.7...1.1)
            let up = SKAction.moveBy(x: 0, y: amplitude, duration: half)
            up.timingMode = .easeInEaseOut
            let down = SKAction.moveBy(x: 0, y: -amplitude, duration: half)
            down.timingMode = .easeInEaseOut
            pair.run(SKAction.repeatForever(SKAction.sequence([up, down, down, up])))
        }
        obstacleLayer.addChild(pair)
        spawnCoin(atX: spawnX, gapCenter: gapCenter, gap: gap)
    }

    /// Wall segment in pair-local coordinates (pair origin sits at y == 0).
    private func makeWall(bottom: CGFloat, height: CGFloat) -> SKNode {
        let wallSize = CGSize(width: wallWidth, height: height)
        let wall = SKShapeNode(rectOf: wallSize, cornerRadius: 4)
        wall.fillColor = SKColor.magenta.withAlphaComponent(0.15)
        wall.strokeColor = SKColor.magenta
        wall.lineWidth = 2
        wall.glowWidth = 5
        wall.position = CGPoint(x: 0, y: bottom + height / 2)

        let body = SKPhysicsBody(rectangleOf: wallSize)
        body.isDynamic = false
        body.categoryBitMask = PhysicsCategory.obstacle
        body.contactTestBitMask = PhysicsCategory.player
        body.collisionBitMask = 0
        wall.physicsBody = body
        return wall
    }

    /// Phase 3: a neon bar spinning around its center.
    private func spawnRotatingBar(offsetX: CGFloat) {
        let barSize = CGSize(width: 250, height: 14)
        let bar = SKShapeNode(rectOf: barSize, cornerRadius: 7)
        bar.fillColor = SKColor.magenta.withAlphaComponent(0.15)
        bar.strokeColor = SKColor.magenta
        bar.lineWidth = 2
        bar.glowWidth = 5

        let minY = gapEdgeMargin + barSize.width / 2
        let maxY = size.height - gapEdgeMargin - barSize.width / 2
        guard maxY > minY else { return }
        bar.position = CGPoint(
            x: size.width + wallWidth + offsetX,
            y: CGFloat.random(in: minY...maxY)
        )
        bar.zRotation = CGFloat.random(in: 0...(2 * .pi))

        let body = SKPhysicsBody(rectangleOf: barSize)
        body.isDynamic = false
        body.categoryBitMask = PhysicsCategory.obstacle
        body.contactTestBitMask = PhysicsCategory.player
        body.collisionBitMask = 0
        bar.physicsBody = body

        let angle: CGFloat = Bool.random() ? 2 * .pi : -2 * .pi
        bar.run(SKAction.repeatForever(
            SKAction.rotate(byAngle: angle, duration: .random(in: 2.0...3.0))
        ))
        obstacleLayer.addChild(bar)
        spawnCoin(atX: bar.position.x, gapCenter: nil, gap: gapHeight)
    }

    /// Bonus coin near the gap — sometimes safely inside it, sometimes at the risky edge.
    private func spawnCoin(atX x: CGFloat, gapCenter: CGFloat?, gap: CGFloat) {
        guard CGFloat.random(in: 0..<1) < coinChance else { return }
        let rawY: CGFloat
        if let gapCenter {
            rawY = gapCenter + CGFloat.random(in: -gap * 0.55...gap * 0.55)
        } else {
            rawY = CGFloat.random(in: gapEdgeMargin...(size.height - gapEdgeMargin))
        }

        let lime = SKColor(red: 0.75, green: 1.0, blue: 0.2, alpha: 1)
        let coin = SKShapeNode(circleOfRadius: coinRadius)
        coin.fillColor = lime
        coin.strokeColor = lime
        coin.glowWidth = 6
        coin.position = CGPoint(
            x: x + 130,
            y: min(max(rawY, coinRadius + 8), size.height - coinRadius - 8)
        )

        let body = SKPhysicsBody(circleOfRadius: coinRadius)
        body.isDynamic = false
        body.categoryBitMask = PhysicsCategory.coin
        body.contactTestBitMask = PhysicsCategory.player
        body.collisionBitMask = 0
        coin.physicsBody = body

        coin.run(SKAction.repeatForever(SKAction.sequence([
            SKAction.scale(to: 1.2, duration: 0.4),
            SKAction.scale(to: 1.0, duration: 0.4),
        ])))
        obstacleLayer.addChild(coin)
    }

    private func updateScore(dt: CGFloat) {
        distance += scrollSpeed * dt
        let newScore = Int(distance * pointsPerPoint) + bonusScore
        if newScore != score {
            score = newScore
            onScoreChanged?(score)
        }
    }

    // MARK: - Contacts

    func didBegin(_ contact: SKPhysicsContact) {
        let mask = contact.bodyA.categoryBitMask | contact.bodyB.categoryBitMask
        if mask & PhysicsCategory.player != 0, mask & PhysicsCategory.obstacle != 0 {
            handleObstacleHit()
        } else if mask & PhysicsCategory.player != 0, mask & PhysicsCategory.coin != 0 {
            let coinBody = contact.bodyA.categoryBitMask == PhysicsCategory.coin
                ? contact.bodyA : contact.bodyB
            if let node = coinBody.node {
                collectCoin(node)
            }
        }
    }

    private func collectCoin(_ node: SKNode) {
        guard !isGameOver else { return }
        let position = node.position
        node.removeFromParent()
        coins += 1
        bonusScore += coinBonus
        onCoinsChanged?(coins)

        AudioService.shared.play(.coin)
        HapticsService.shared.impact(.light)
        burstParticles(
            at: position,
            color: SKColor(red: 0.75, green: 1.0, blue: 0.2, alpha: 1),
            count: 14, speed: 180, scale: 0.35
        )
    }

    private func handleObstacleHit() {
        guard !isInvincible, !isGameOver else { return }
        lives -= 1
        onLivesChanged?(lives)

        AudioService.shared.play(.hit)
        HapticsService.shared.impact(.heavy)
        shakeCamera()
        flash(color: SKColor(red: 1, green: 0.25, blue: 0.4, alpha: 1), maxAlpha: 0.4)
        burstParticles(at: player.position, color: .magenta, count: 24, speed: 260, scale: 0.4)

        if lives <= 0 {
            gameOver()
            return
        }

        isInvincible = true
        let blink = SKAction.sequence([
            SKAction.fadeAlpha(to: 0.2, duration: 0.1),
            SKAction.fadeAlpha(to: 1.0, duration: 0.1),
        ])
        let blinkCount = Int(invincibleDuration / 0.2)
        player.run(SKAction.repeat(blink, count: blinkCount)) { [weak self] in
            self?.player.alpha = 1
            self?.isInvincible = false
        }
    }

    private func gameOver() {
        isGameOver = true
        isThrusting = false
        player.removeAllActions()
        player.alpha = 1

        // Explosion in frozen time (update() stops), then hand off to SwiftUI.
        player.isHidden = true
        burstParticles(at: player.position, color: .cyan, count: 70, speed: 420, scale: 0.7)
        flash(color: .white, maxAlpha: 0.55)
        shakeCamera(amplitude: 16)
        AudioService.shared.play(.gameOver)
        HapticsService.shared.gameOver()
        AudioService.shared.stopBGM(fadeOut: 0.6)

        run(SKAction.wait(forDuration: 0.8)) { [weak self] in
            guard let self else { return }
            self.onGameOver?(self.score)
        }
    }

    // MARK: - Effects

    private func shakeCamera(amplitude: CGFloat = 9) {
        cameraNode.removeAction(forKey: "shake")
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        var steps: [SKAction] = []
        for i in 0..<6 {
            let falloff = amplitude * (1 - CGFloat(i) / 6)
            let offset = CGPoint(
                x: center.x + CGFloat.random(in: -falloff...falloff),
                y: center.y + CGFloat.random(in: -falloff...falloff)
            )
            steps.append(SKAction.move(to: offset, duration: 0.04))
        }
        steps.append(SKAction.move(to: center, duration: 0.04))
        cameraNode.run(SKAction.sequence(steps), withKey: "shake")
    }

    private func flash(color: SKColor, maxAlpha: CGFloat) {
        flashNode.color = color
        flashNode.removeAllActions()
        flashNode.alpha = maxAlpha
        flashNode.run(SKAction.fadeAlpha(to: 0, duration: 0.25))
    }

    private func burstParticles(
        at position: CGPoint, color: SKColor, count: Int, speed: CGFloat, scale: CGFloat
    ) {
        let emitter = SKEmitterNode()
        emitter.particleTexture = particleTexture
        emitter.numParticlesToEmit = count
        emitter.particleBirthRate = CGFloat(count) * 20
        emitter.particleLifetime = 0.5
        emitter.particleLifetimeRange = 0.25
        emitter.particleSpeed = speed
        emitter.particleSpeedRange = speed * 0.6
        emitter.emissionAngleRange = .pi * 2
        emitter.particleAlpha = 0.9
        emitter.particleAlphaSpeed = -1.6
        emitter.particleScale = scale
        emitter.particleScaleSpeed = -scale
        emitter.particleColor = color
        emitter.particleColorBlendFactor = 1
        emitter.particleBlendMode = .add
        emitter.position = position
        emitter.zPosition = 50
        addChild(emitter)
        emitter.run(SKAction.sequence([SKAction.wait(forDuration: 1.2), SKAction.removeFromParent()]))
    }
}
