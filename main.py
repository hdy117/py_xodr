import os
import sys
import constants
import road_network
import argparse
import logging

def add_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--xodr", type=str, required=True)
    return parser.parse_args()

def config_logging():
    logging.basicConfig(
        format="%(asctime)s--%(filename)s[%(lineno)d][%(levelname)s]--%(message)s",
        level=logging.INFO
    )
    logging.basicConfig(level=logging.INFO)
    logging.info("Logging configured")

if __name__ == "__main__":
    config_logging()

    args = add_arguments()
    xodr_file = args.xodr

    road_network = road_network.RoadNetwork(xodr_file)
    if road_network.parse_xodr() != constants.ErrorCode.OK:
        logging.error(f"Failed to parse xodr file: {xodr_file}")
        sys.exit(1)
    else:
        road_network.sample_roads()
        logging.info(f"XODR file parsed successfully: {xodr_file}")
