import sys,pstats

stats = pstats.Stats(sys.argv[1])
stats.strip_dirs()
stats.sort_stats('tottime')
stats.print_stats(0.2)
stats.print_callees()
stats.print_callers()
