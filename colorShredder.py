import colorTools
import config
import bruteForceShredder
import rTreeShredder

def main():
    if (config.PARSED_ARGS.t):
        rTreeShredder.shredColors()
    else:
        bruteForceShredder.shredColors()


if __name__ == '__main__':
    main()