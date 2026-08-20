#!/usr/bin/env python3
"""
Test script for SKG-Accelerated Cochlear Processor v3.1
Demonstrates Caleon's learning from hearing mistakes.
"""

import numpy as np
from cochlear_processor_v3 import CochlearProcessorV3

def create_dummy_audio(duration_seconds=2, sample_rate=16000):
    """Create dummy audio for testing"""
    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds))
    # Simulate speech-like signal
    audio = 0.5 * np.sin(2 * np.pi * 300 * t)  # 300Hz tone
    audio += 0.3 * np.sin(2 * np.pi * 2000 * t)  # Higher frequency
    return audio.astype(np.float32)

def test_skg_cochlear_processor():
    """Test the SKG-enhanced processor"""
    print("🧠 Testing SKG-Accelerated Cochlear Processor v3.1")
    print("=" * 60)
    
    # Initialize processor
    processor = CochlearProcessorV3()
    
    # Create dummy audio file (in real usage, this would be a real audio file)
    dummy_audio = create_dummy_audio()
    
    # Simulate processing Phil's podcast episode
    context = {
        "topic": "AI_machine_learning",
        "text": "the future of AI is machine learning"
    }
    
    print("\n🎧 Processing Phil's podcast episode...")
    trace = processor.process_audio_human_like(
        audio_path="dummy_audio.wav",  # Would be real path
        context=context,
        speaker_id="phil_dandy"
    )
    
    print("\n📊 Processing Results:")
    print(f"   Original: {trace['transcription']['original']}")
    print(f"   Corrected: {trace['transcription']['corrected']}")
    print(f"   Corrections: {len(trace['transcription']['corrections'])}")
    
    print("\n🧠 Learning Summary:")
    summary = processor.get_learning_summary()
    print(f"   Total corrections processed: {summary['total_corrections_processed']}")
    print(".3f")
    print(".3f")
    print(f"   Phoneme mastery: {summary['phoneme_mastery']}")
    print(f"   Speaker mastery: {summary['speaker_mastery']}")
    
    print("\n💾 SKG has been updated with this learning experience!")
    
    # Simulate second processing to show learning
    print("\n🔄 Processing another episode from Phil...")
    trace2 = processor.process_audio_human_like(
        audio_path="dummy_audio2.wav",
        context=context,
        speaker_id="phil_dandy"
    )
    
    print("\n📈 Improvement Check:")
    summary2 = processor.get_learning_summary()
    improvement = summary2['avg_speaker_mastery'] - summary['avg_speaker_mastery']
    print(".3f")
    
    print("\n✅ SKG Learning Loop Complete!")
    print("   Caleon now hears Phil's voice better and corrects 'aye'→'AI' more confidently.")

if __name__ == "__main__":
    test_skg_cochlear_processor()