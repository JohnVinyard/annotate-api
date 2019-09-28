import argparse
from cli import DefaultArgumentParser
from client import Client
from s3client import ObjectStorageClient
import requests
import urllib
from io import BytesIO
import soundfile
from http import client
from log import module_logger
from mp3encoder import encode_mp3
from pathlib import Path
import zounds

logger = module_logger(__file__)

datasets = [

    # Classical
    zounds.InternetArchive('AOC11B'),
    zounds.InternetArchive('CHOPINBallades-NEWTRANSFER'),
    zounds.InternetArchive('JohnCage'),
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[
        DefaultArgumentParser()
    ])
    args = parser.parse_args()
    annotate_client = Client(args.annotate_api_endpoint, logger=logger)

    bucket_name = 'internet-archive'
    info_url = 'https://archive.org/details/audio?tab=about'

    object_storage_client = ObjectStorageClient(
        endpoint=args.s3_endpoint,
        region=args.s3_region,
        access_key=args.aws_access_key_id,
        secret=args.aws_secret_access_key,
        bucket=bucket_name)
    object_storage_client.ensure_bucket_exists()

    annotate_client.upsert_dataset(
        user_name='internetarchive',
        email='john.vinyard+internet-archive-dataset@gmail.com',
        password=args.password,
        about_me='I am the internet',
        info_url=info_url)

    import random
    random.shuffle(datasets)

    for dataset in datasets:
        for item in dataset:
            session = requests.Session()
            prepped = item.request.prepare()
            resp = session.send(prepped)
            bio = BytesIO(resp.content)
            logger.info(item)

            try:
                encoded = encode_mp3(bio)
            except RuntimeError:
                logger.info(
                    f'Error decoding audio for {item.request.url}. Skipping.')
                continue

            path = Path(urllib.parse.urlparse(item.request.url).path)
            relative_path = path.relative_to('/download').with_suffix('')

            low_quality_id = \
                str(Path('low-quality') / relative_path.with_suffix('.mp3'))
            low_quality_url = object_storage_client.put_object(
                low_quality_id, encoded, 'audio/mp3')
            logger.info(f'Pushed {low_quality_url} to s3')
            bio.seek(0)

            _id = str(relative_path.with_suffix('.wav'))
            url = object_storage_client.put_object(_id, bio, 'audio/wav')
            logger.info(f'Pushed audio data for {url} to s3')
            bio.seek(0)

            info = soundfile.info(bio)

            status, sound_uri, sound_id = annotate_client.create_sound(
                audio_url=url,
                low_quality_audio_url=low_quality_url,
                info_url=info_url,
                # TODO: Get creative commons license from each dataset
                license_type='https://creativecommons.org/licenses/by-nc-nd/4.0',
                title=str(relative_path),
                duration_seconds=info.duration)
            logger.info(f'Created sound resource {sound_uri}')
            if status == client.CREATED:
                if item.tags:
                    annotate_client.create_annotations(
                        sound_id,
                        {
                            'start_seconds': 0,
                            'duration_seconds': info.duration,
                            'tags': item.tags
                        }
                    )
                    logger.info(f'Created annotation with tags {item.tags} for {sound_uri}')
            elif status == client.CONFLICT:
                logger.warning(
                    f'Already created sound and annotation for {sound_uri}')
                # we've already created this sound and annotation
                pass
            else:
                raise RuntimeError(f'Unexpected {status} encountered')
