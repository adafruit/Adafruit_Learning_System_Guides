import puff_detector

detector = puff_detector.PuffDetector()


@detector.on_sip
def on_sip(strength, duration):
    if strength == puff_detector.STRONG:
        strength_str = "STRONG"
    if strength == puff_detector.SOFT:
        strength_str = "SOFT"
    log_str = "DETECTED::SIP:%s::DURATION:%0.3f" % (strength_str, duration)
    print(log_str)


@detector.on_puff
def on_puff(strength, duration):
    if strength == puff_detector.STRONG:
        strength_str = "STRONG"
    if strength == puff_detector.SOFT:
        strength_str = "SOFT"
    log_str = "DETECTED::PUFF:%s::DURATION:%0.3f" % (strength_str, duration)
    print(log_str)


detector.run()
