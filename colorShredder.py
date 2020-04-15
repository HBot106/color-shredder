import colorTools
import config
import bruteForceShredder
import rTreeShredder

def main():
    if (not config.PARSED_ARGS.t):
        bruteForceShredder.shredColors()
    else:
        rTreeShredder.shredColors()


if __name__ == '__main__':
    main()