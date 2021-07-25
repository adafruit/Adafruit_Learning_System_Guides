import puff_detector

detector = puff_detector.PuffDetector()


@detector.on_sip
def on_sip(strength, duration):
    if strength == puff_detector.STRONG:
        print("GOT STRONG SIP")
    if strength == puff_detector.SOFT:
        print("GOT SOFT SIP")
    print("%.2f long" % duration)


@detector.on_puff
def on_puff(strength, duration):
    if strength == puff_detector.STRONG:
        print("GOT STRONG PUFF")
    if strength == puff_detector.SOFT:
        print("GOT SOFT PUFF")
    print("%.2f long" % duration)


detector.run()
