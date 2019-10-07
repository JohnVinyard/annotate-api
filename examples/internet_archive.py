import argparse
from cli import DefaultArgumentParser
from client import Client
import requests
import urllib
from io import BytesIO
from log import module_logger
from pathlib import Path
import zounds
from bot_helper import BotDriver
from urllib.parse import urlparse

logger = module_logger(__file__)

datasets = [

    # Classical
    zounds.InternetArchive('AOC11B'),
    zounds.InternetArchive('CHOPINBallades-NEWTRANSFER'),
    zounds.InternetArchive('beethoven_ingigong_850'),
    zounds.InternetArchive('jamendo-086440'),
    zounds.InternetArchive('The_Four_Seasons_Vivaldi-10361'),

    # Pop
    zounds.InternetArchive('02.LostInTheShadowsLouGramm'),
    zounds.InternetArchive('08Scandalous'),
    zounds.InternetArchive('09.JoyceKennedyDidntITellYou'),
    zounds.InternetArchive('02.InThisCountryRobinZander'),
    zounds.InternetArchive('PeterGabrielOutOut'),
    zounds.InternetArchive('07.SpeedOfLightJoeSatriani'),

    # Jazz
    zounds.InternetArchive('Free_20s_Jazz_Collection'),

    # Hip Hop
    zounds.InternetArchive('LucaBrasi2'),
    zounds.InternetArchive('Chance_The_Rapper_-_Coloring_Book'),
    zounds.InternetArchive('Chance_The_Rapper_-_Acid_Rap-2013'),
    zounds.InternetArchive('Kevin_Gates_-_By_Any_Means-2014'),
    zounds.InternetArchive('Lil_Wayne_-_Public_Enemy'),
    zounds.InternetArchive('Chance_The_Rapper_-_Good_Enough'),

    # Speech
    zounds.InternetArchive('Greatest_Speeches_of_the_20th_Century'),
    zounds.InternetArchive(
        'cd_great-speeches-and-soliloquies_william-shakespeare'),
    zounds.InternetArchive('The_Speeches-8291'),
    zounds.InternetArchive('RasKitchen'),

    # Electronic
    zounds.InternetArchive('rome_sample_pack'),
    zounds.InternetArchive('CityGenetic'),
    zounds.InternetArchive('SvenMeyer-KickSamplePack'),
    zounds.InternetArchive('jamendo-046316'),
    zounds.InternetArchive('jamendo-079926'),
    zounds.InternetArchive('jamendo-069115'),
    zounds.InternetArchive('SampleScienceToyKeyboardSamples'),
    zounds.InternetArchive('jamendo-071495'),
    zounds.InternetArchive('HgfortuneTheTygerSynth'),
    zounds.InternetArchive('mellow-jeremy-synth-technology'),
    zounds.InternetArchive('RandomSynth2'),
    zounds.InternetArchive('Mc303Synth'),
    zounds.InternetArchive('HalloweenStickSynthRaver'),

    # Nintendo
    zounds.InternetArchive('CastlevaniaNESMusicStage10WalkingOnTheEdge'),
    zounds.InternetArchive(
        'BloodyTearsSSHRemixCastlevaniaIISimonsQuestMusicExtended'),
    zounds.InternetArchive(
        'CastlevaniaIIIDraculasCurseNESMusicEnterNameEpitaph'),
    zounds.InternetArchive('SuperMarioBros3NESMusicWorldMap6'),
    zounds.InternetArchive('SuperMarioBrosNESMusicHurriedOverworld'),
    zounds.InternetArchive('AdventuresOfGilligansIslandTheSoundtrack1NESMusic'),
    zounds.InternetArchive('SuperMarioWorldSNESMusicUndergroundThemeYoshi'),
]


class InternetArchiveBot(object):
    def     __init__(self):
        super().__init__()
        self.user_name = 'internetarchive'
        self.bucket_name = 'internet-archive'
        self.info_url = 'https://archive.org/details/audio?tab=about'
        self.about_me = 'internet_archive.md'
        self.email = 'john.vinyard+internet-archive@gmail.com'

    def iter_sounds(self):
        for dataset in datasets:
            for item in dataset:
                session = requests.Session()
                prepped = item.request.prepare()
                resp = session.send(prepped)
                bio = BytesIO(resp.content)
                logger.info(item)
                path = Path(urllib.parse.urlparse(item.request.url).path)
                relative_path = path.relative_to('/download').with_suffix('')
                meta = requests.get(
                    self._details_url(relative_path), params={'output': 'json'})
                yield str(relative_path), bio, meta.json()

    def _details_url(self, name):
        segments = str(name).split('/')
        _id = segments[0]
        return f'https://archive.org/details/{_id}'

    def get_info_url(self, name, metadata):
        return self._details_url(name)

    def get_license_type(self, name, metadata):
        try:
            license_type = metadata['license_url']
            parsed = urlparse(license_type)
            path = Path(parsed.path)
            updated = parsed._replace(
                scheme='https', path=str(path.with_name('4.0')))
            return updated.geturl()
        except KeyError:
            # If there is no license, assume the most restrictive license
            return 'https://creativecommons.org/licenses/by-nc-nd/4.0'

    def get_annotations(self, name, metadta, bio):
        return []


if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[
        DefaultArgumentParser()
    ])
    args = parser.parse_args()
    annotate_client = Client(args.annotate_api_endpoint, logger=logger)
    bot = InternetArchiveBot()

    driver = BotDriver(args, logger, bot)
    driver.run()
