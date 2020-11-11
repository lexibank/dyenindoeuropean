import collections
import pathlib
import re

import attr
from clldutils.misc import nfilter
from pylexibank import Dataset as BaseDataset
from pylexibank import Language


@attr.s
class CustomLanguage(Language):
    Details = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "dyenindoeuropean"

    def cmd_makecldf(self, args):
        args.writer.add_sources()
        langs = {lang['Name']: lang['Glottocode'] for lang in self.languages}

        concepticon = {c.number: c.concepticon_id for c in self.conceptlists[0].concepts.values()}
        varieties, meanings, allforms, rels = parse(self)

        for mn, cognatesets in sorted(allforms.items()):
            args.writer.add_concept(ID=mn, Name=meanings[mn], Concepticon_ID=concepticon[mn])
            for ccn, forms in sorted(cognatesets.items()):
                for ln, form in forms:
                    args.writer.add_language(
                        ID=ln,
                        Name=varieties[ln]["name"].strip(),
                        Glottocode=langs[varieties[ln]["name"].strip()],
                    )
                    ffs = [ff.strip().lower() for ff in form.split(",")]
                    for i, f in enumerate(nfilter(ffs)):
                        for row in args.writer.add_lexemes(
                            Language_ID=ln,
                            Parameter_ID=mn,
                            Value=f,
                            Source=["Dyen1992"],
                            Cognacy="%s-%s" % (mn, ccn),
                        ):
                            if len(ffs) == 1 and (2 <= int(ccn) <= 99 or 200 <= int(ccn) <= 399):
                                # most conservative cognacy judgements only
                                args.writer.add_cognate(
                                    lexeme=row, Cognateset_ID="%s-%s" % (mn, ccn)
                                )


HEADER = re.compile(r"a (?P<number>[0-9]{3}) (?P<label>.+)")
SUBHEADER = re.compile(r"b\s+(?P<ccn>[0-9]+)$")
RELATION = re.compile(r"c\s+(?P<ccn1>[0-9]+)\s+(?P<relation>[23])\s+(?P<ccn2>[0-9]+)$")
FORM = re.compile(r"\s+(?P<mn>[0-9]{3})\s+(?P<ln>[0-9]{2})\s+(?P<variety>.{15})\s+(?P<forms>.*)")
MISSING_FORM = re.compile(r"\s+(?P<mn>[0-9]{3})\s+(?P<ln>[0-9]{2})\s+(?P<variety>.{1,15})$")
VARIETY = re.compile(
    r".{16} (?P<num>[0-9]{2}) (?P<name>.{15}) (?P<onum>[0-9]{2}) "
    r"(?P<oname>.{15}) (?P<count>[0-9]{3})"
)


def blocks(lines, pattern):
    md, block = None, []
    for line in lines:
        match = pattern.match(line)
        if match:
            if md:
                yield md, block
            md, block = match.groupdict(), []
        elif md:
            block.append(line)
    if md:
        yield md, block


def relations_and_forms(lines):
    rels, forms, missing = [], [], []
    for line in lines:
        if not line.strip():
            missing.append(line)
            continue
        match = RELATION.match(line)
        if match:
            rels.append((match.group("ccn1"), match.group("relation"), match.group("ccn2")))
        else:
            match = FORM.match(line)
            if match:
                d = match.groupdict()
                forms.append((d["mn"], d["ln"], d["variety"].strip(), d["forms"].strip()))
            else:
                assert MISSING_FORM.match(line)
                missing.append(line)
    return rels, forms, missing


def parse(dataset):
    lines, in_data, varieties, meanings = [], False, {}, {}
    for line in dataset.raw_dir.read("iedata-with-intro.txt").split("\n"):
        if in_data:
            lines.append(line)
        else:
            match = VARIETY.match(line)
            if match:
                varieties[match.group("num")] = match.groupdict()
        if line == "5. THE DATA":
            in_data = True

    meanings_per_variety = collections.Counter()
    rels, forms = (
        collections.defaultdict(set),
        collections.defaultdict(lambda: collections.defaultdict(list)),
    )
    for md, block in blocks(lines, HEADER):
        mn = md["number"]
        meanings[mn] = md["label"]
        for md2, subblock in blocks(block, SUBHEADER):
            r, f, m = relations_and_forms(subblock)
            assert len(r) + len(f) + len(m) == len(subblock)
            for rr in r:
                rels[mn].add(rr)
            for _, ln, variety, forms_ in f:
                assert _ == mn and ln in varieties
                meanings_per_variety.update([ln])
                if md2["ccn"] != "000":  # discard inappropriate forms.
                    forms[mn][md2["ccn"]].append((ln, forms_))
    for mn, rels_ in rels.items():
        for s, _, t in rels_:
            assert int(s) >= 200 and int(t) >= 200 and s in forms[mn] and t in forms[mn]

    assert all(n == int(varieties[ln]["count"]) for ln, n in meanings_per_variety.items())
    return varieties, meanings, forms, rels
