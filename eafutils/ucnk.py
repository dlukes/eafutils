#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""A module for dealing with the .eaf transcription format as used in the
ORTOFON multi-tier spoken corpus project at ÚČNK.

"""

import os
import fnmatch
import re
import xml.etree.ElementTree as ET
import random
# from collections import defaultdict
# from sys import stderr, argv, exit
# from signal import signal, SIGPIPE, SIG_DFL

# signal(SIGPIPE, SIG_DFL)

ANOM = set(["NJ", "NN", "NM", "NO", "NT"])


class OrtofonEaf(ET.ElementTree):
    """An abstraction for querying and modifying an .eaf XML tree representing a
    transcription corresponding to the requirements of the ORTOFON project.

    """

    _ort_dict = None
    """A dict with all the annotations on the ort layer. Initialized on demand.
    """

    _fon_dict = None
    """A dict with all the annotations on the fon layer. Initialized on demand.
    """

    _time_dict = None
    """A dict with all the time slots. Initialized on demand."""

    def __init__(self, file):
        super().__init__(file=file)
        self.ort = self._extract_annotations_in_tier("ortografický", True)
        self.fon = self._extract_annotations_in_tier("fonetický", True)
        self.time = self._extract_timestamps()

    def ort_dict(self):
        if self._ort_dict:
            return self._ort_dict
        else:
            self._ort_dict = self._lst2dict(self.ort, "ANNOTATION_ID")
            return self._ort_dict

    def fon_dict(self):
        if self._fon_dict:
            return self._fon_dict
        else:
            self._fon_dict = self._lst2dict(self.fon, "ANNOTATION_ID")
            return self._fon_dict

    def fon_dict_by_ort_id(self):
        if self._fon_dict:
            return self._fon_dict
        else:
            self._fon_dict = self._lst2dict(self.fon, "ANNOTATION_REF")
            return self._fon_dict

    def time_dict(self):
        if self._time_dict:
            return self._time_dict
        else:
            self._time_dict = self._lst2dict(self.time, "TIME_SLOT_ID")
            return self._time_dict

    def _lst2dict(self, lst, key):
        """Convert list of dicts to a dict of dicts keyed by their dict[key].

        Args:

            lst: a list of dicts
            key: dict[key] will be used to key each dict in lst in the output
            dict

        """
        return {d[key]: d for d in lst}

    def _extract_annotations_in_tier(self, attrib, get_attribs=False):
        """Extract annotations in transcription tier with attribute attrib.

        Attrib is checked against the LINGUISTIC_TYPE_REF attribute of each
        TIER element.

        Args:

            attrib: a string
            get_attribs: Boolean

        Returns:

            A list of annotations from tier with given attribute as
            consecutively encountered in transcription. If XML attributes of
            the entries are required (get_attribs=True), the list contains one
            tuple with a string and a dictionary of attribs per entry.

        """
        root = self.getroot()
        annots = []
        annot_type = ("REF_ANNOTATION" if (attrib == "fonetický") else
                      "ALIGNABLE_ANNOTATION")
        for tier in root.iter("TIER"):
            # ignore tiers added by TransVer
            if tier.attrib["LINGUISTIC_TYPE_REF"] == attrib and \
               tier.attrib.get("ANNOTATOR") != "TransVer" and \
               not tier.attrib.get("TIER_ID").startswith("JO") and \
               not tier.attrib.get("TIER_ID").startswith("anom"):
                speaker = tier.attrib["TIER_ID"].split()[0]
                for annot in tier.iter(annot_type):
                    annot_text = annot.getchildren()[0].text
                    if get_attribs:
                        annot = annot.attrib
                        annot["ANNOTATION_VALUE"] = annot_text
                        annot["SPEAKER"] = speaker
                        annots.append(annot)
                    else:
                        annots.append(annot_text)
        return annots

    def _extract_timestamps(self):
        """Extract timestamps from transcription.

        Timestamps are TIME_SLOT children of the TIME_ORDER element.
        """
        root = self.getroot()
        timestamps = []
        for time_slot in root.iter("TIME_SLOT"):
            timestamps.append(time_slot.attrib)
        return timestamps


def random_anom():
    """Return a random anonymization code."""
    return random.sample(ANOM, 1)[0]

def kaldi_tokenize(annotation):
    # remove chars which are not relevant for kaldi transcript
    annotation = re.sub(r"[\?#\$\[\]\{\}\(\)=>\-\*\+_]", "", annotation)
    annotation = re.sub("<[A-Z]+ ", "", annotation)
    # replace unknown words represented by digits with a random anonymization
    # sequence
    annotation = re.sub(r"\d+", random_anom(), annotation)
    # and split on pipes and whitespace+ (+ strip before splitting to avoid
    # empty strings at extremities):
    return re.split(r"\||\s+", annotation.strip())

def to_split_phones(fon_word):
    """Convert a single phonetically transcribed word to a format where phones
    are explicitly whitespace separated.

    E.g.: "chroust" -> "ch r ou s t"

    NOTE: hmm, emm and ANY string containing non-word characters (acc. to
    Unicode) or uppercase A-Z (anonymization codes) are returned is (they are
    considered atomic units).

    """
    # only transcriptions which are all lowercase letters actually consist of
    # separable phones; other "words" should be returned as is
    if re.search(r"[\WA-Z]", fon_word) or fon_word in ("hmm", "emm"):
        return fon_word
    else:
        # split fon_word and re-join it with spaces
        fon_word = " ".join(list(fon_word))
        # collapse digraphs back together
        fon_word = re.sub("c h", "ch", fon_word)
        fon_word = re.sub("o u", "ou", fon_word)
        return re.sub("ʒ ʒ", "ʒʒ", fon_word)

def find_eaf(directory):
    matches = []
    for root, dirnames, filenames in os.walk(directory):
        for filename in fnmatch.filter(filenames, "*.eaf"):
            matches.append(os.path.join(root, filename))
    return matches
