import AVFoundation
import Foundation

enum TTSError: Error {
    case missingArguments
    case invalidEncoding
    case voiceUnavailable
    case writeFailed
}

let arguments = CommandLine.arguments
guard arguments.count >= 3 else {
    throw TTSError.missingArguments
}

let outputPath = arguments[1]
let text = arguments[2]

let voice = AVSpeechSynthesisVoice(language: "zh-CN") ?? AVSpeechSynthesisVoice(language: "zh-TW")
guard voice != nil else {
    throw TTSError.voiceUnavailable
}

let utterance = AVSpeechUtterance(string: text)
utterance.voice = voice
utterance.rate = 0.53
utterance.pitchMultiplier = 0.92
utterance.volume = 1.0
utterance.preUtteranceDelay = 0
utterance.postUtteranceDelay = 0

let outputURL = URL(fileURLWithPath: outputPath)
try? FileManager.default.removeItem(at: outputURL)

let settings: [String: Any] = [
    AVFormatIDKey: kAudioFormatLinearPCM,
    AVSampleRateKey: 22050,
    AVNumberOfChannelsKey: 1,
    AVLinearPCMBitDepthKey: 16,
    AVLinearPCMIsFloatKey: false,
    AVLinearPCMIsBigEndianKey: false,
]

let audioFile = try AVAudioFile(
    forWriting: outputURL,
    settings: settings,
    commonFormat: .pcmFormatInt16,
    interleaved: false
)

let synthesizer = AVSpeechSynthesizer()
let group = DispatchGroup()
var wroteFrames = false

group.enter()
synthesizer.write(utterance) { buffer in
    guard let pcmBuffer = buffer as? AVAudioPCMBuffer else {
        return
    }

    if pcmBuffer.frameLength == 0 {
        group.leave()
        return
    }

    do {
        try audioFile.write(from: pcmBuffer)
        wroteFrames = true
    } catch {
        group.leave()
    }
}

group.wait()

if !wroteFrames {
    throw TTSError.writeFailed
}
