//
//  My_TianjinApp.swift
//  My Tianjin
//
//  Created by Kazumasa Ikeuchi on 2026/07/13.
//

import SwiftUI
import SwiftData

@main
struct My_TianjinApp: App {
    @StateObject private var contentStore = LearningContentStore()
    @StateObject private var speechService = SpeechService()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(contentStore)
                .environmentObject(speechService)
        }
        .modelContainer(for: [
            StudyProgressRecord.self,
            StudySessionRecord.self,
            ConversationSessionRecord.self
        ])
    }
}
