from Integration import TPCSystem

tpc = TPCSystem()
tpc.initialize()
result = tpc.process('The sky is blue', 'text')

print('Philosopher Verdicts:')
for phil, data in result['philosopher_results'].items():
    print(f'  {phil}: {data["verdict"]} (conf: {data["confidence"]:.3f})')

print(f'Synthesis confidence: {result["synthesis"]["confidence"]:.3f}')
print(f'Final conclusion: {result["synthesis"]["final_conclusion"]}')