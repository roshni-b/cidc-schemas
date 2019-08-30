#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for PRISM the module which pulls JSON objects from excel spreadsheets."""

import os
import copy
import pytest
import jsonschema
import json
from deepdiff import grep, DeepDiff
from pprint import pprint
from jsonmerge import Merger

from cidc_schemas.prism import prismify, merge_artifact, \
    merge_clinical_trial_metadata, InvalidTargetException
from cidc_schemas.json_validation import load_and_validate_schema
from cidc_schemas.template import Template
from cidc_schemas.template_writer import RowType
from cidc_schemas.template_reader import XlTemplateReader

from .constants import ROOT_DIR, SCHEMA_DIR, TEMPLATE_EXAMPLES_DIR
from .test_templates import template_paths
from .test_assays import ARTIFACT_OBJ


WES_TEMPLATE_EXAMPLE_CT = {
        "lead_organization_study_id": "10021",
        "participants": [
            {
                "samples": [
                    {
                        "aliquots": [
                            {
                                "cimac_aliquot_id": "wes example aliquot 1.1.1",
                                "units": "Other",
                                "material_used": 1,
                                "material_remaining": 0,
                                "aliquot_quality_status": "Other",
                                "aliquot_replacement": "N/A",
                                "aliquot_status": "Other"
                            },
                        ],
                        "cimac_sample_id": "wes example SA 1.1",
                        "site_sample_id": "site sample 1",
                        "time_point": "---",
                        "sample_location": "---",
                        "specimen_type": "Other",
                        "specimen_format": "Other",
                        "genomic_source": "Tumor",
                    }
                ],
                "cimac_participant_id": "wes example PA 1",
                "trial_participant_id": "trial patient 1",
                "cohort_id": "---",
                "arm_id": "---"
            },
            {
                "samples": [
                    {
                        "aliquots": [
                            {
                                "cimac_aliquot_id": "wes example aliquot 1.2.1",
                                "units": "Other",
                                "material_used": 2,
                                "material_remaining": 0,
                                "aliquot_quality_status": "Other",
                                "aliquot_replacement": "N/A",
                                "aliquot_status": "Other"
                            }
                        ],
                        "cimac_sample_id": "wes example SA 2.1",
                        "site_sample_id": "site sample 2",
                        "time_point": "---",
                        "sample_location": "---",
                        "specimen_type": "Other",
                        "specimen_format": "Other",
                        "genomic_source": "Tumor",
                    }
                ],
                "cimac_participant_id": "wes example PA 2",
                "trial_participant_id": "trial patient 2",
                "cohort_id": "---",
                "arm_id": "---"
            }
        ],
        "assays": {
            "wes": [
                {
                    "assay_creator": "Mount Sinai",
                    "enrichment_vendor_kit": "Twist",
                    "library_vendor_kit": "KAPA - Hyper Prep",
                    "sequencer_platform": "Illumina - NextSeq 550",
                    "paired_end_reads": "Paired",
                    "read_length": 100,
                    "records": [
                        {
                            "library_kit_lot": "lib lot 1",
                            "enrichment_vendor_lot": "enrich lot 1",
                            "library_prep_date": "2019-01-01 00:00:00",
                            "capture_date": "2019-01-01 00:00:00",
                            "input_ng": 101,
                            "library_yield_ng": 701,
                            "average_insert_size": 251,
                            "cimac_participant_id": "wes example PA 1",
                            "cimac_sample_id": "wes example SA 1.1",
                            "cimac_aliquot_id": "wes example aliquot 1.1.1",
                            "files": {
                                "fastq_1": {
                                    "upload_placeholder": "fastq_1.1"
                                },
                                "fastq_2": {
                                    "upload_placeholder": "fastq_2.1"
                                },
                                "read_group_mapping_file": {
                                    "upload_placeholder": "read_group_mapping_file.1"
                                }
                            }
                        },
                        {
                            "library_kit_lot": "lib lot 2",
                            "enrichment_vendor_lot": "enrich lot 2",
                            "library_prep_date": "2019-02-02 00:00:00",
                            "capture_date": "2019-02-02 00:00:00",
                            "input_ng": 102,
                            "library_yield_ng": 702,
                            "average_insert_size": 252,
                            "cimac_participant_id": "wes example PA 2",
                            "cimac_sample_id": "wes example SA 2.1",
                            "cimac_aliquot_id": "wes example aliquot 1.2.1",
                            "files": {
                                "fastq_1": {
                                    "upload_placeholder": "fastq_1.2"
                                },
                                "fastq_2": {
                                    "upload_placeholder": "fastq_2.2"
                                },
                                "read_group_mapping_file": {
                                    "upload_placeholder": "read_group_mapping_file.2"
                                }
                            }
                        }
                    ]
                }
            ]
        }
    }


# corresponding list of gs_urls.
WES_TEMPLATE_EXAMPLE_GS_URLS = [
    'wes example PA 1/wes example SA 1.1/wes example aliquot 1.1.1/wes/fastq_1/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx1',
    'wes example PA 1/wes example SA 1.1/wes example aliquot 1.1.1/wes/fastq_2/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx2',
    'wes example PA 1/wes example SA 1.1/wes example aliquot 1.1.1/wes/read_group_mapping_file/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx3',
    'wes example PA 2/wes example SA 2.1/wes example aliquot 1.2.1/wes/fastq_1/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx4',
    'wes example PA 2/wes example SA 2.1/wes example aliquot 1.2.1/wes/fastq_2/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx5',
    'wes example PA 2/wes example SA 2.1/wes example aliquot 1.2.1/wes/read_group_mapping_file/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx6'
]


def test_merge_core():

    # create aliquot
    aliquot = {
        "cimac_aliquot_id": "1234",
        "units": "Other",
        "material_used": 1,
        "material_remaining": 0,
        "aliquot_quality_status": "Other",
        "aliquot_replacement": "N/A",
        "aliquot_status": "Other"
    }

    # create the sample.
    sample = {
        "cimac_sample_id": "S1234",
        "site_sample_id": "blank",
        "aliquots": [aliquot],
        "time_point": "---",
        "sample_location": "---",
        "specimen_type": "Other",
        "specimen_format": "Other",
        "genomic_source": "Tumor",
    }

    # create the participant
    participant = {
        "cimac_participant_id": "P1234",
        "trial_participant_id": "blank",
        "samples": [sample],
        "cohort_id": "---",
        "arm_id": "---"
    }

    # create the trial
    ct1 = {
        "lead_organization_study_id": "test",
        "participants": [participant]
    }

    # create validator assert schemas are valid.
    validator = load_and_validate_schema("clinical_trial.json", return_validator=True)
    schema = validator.schema
    validator.validate(ct1)

    # create a copy of this, modify participant id
    ct2 = copy.deepcopy(ct1)
    ct2['participants'][0]['cimac_participant_id'] = "PABCD"

    # merge them
    merger = Merger(schema)
    ct3 = merger.merge(ct1, ct2)

    # assert we have two participants and their ids are different.
    assert len(ct3['participants']) == 2
    assert ct3['participants'][0]['cimac_participant_id'] == ct1['participants'][0]['cimac_participant_id']
    assert ct3['participants'][1]['cimac_participant_id'] == ct2['participants'][0]['cimac_participant_id']

    # now lets add a new sample to one of the participants
    ct4 = copy.deepcopy(ct3)
    sample2 = ct4['participants'][0]['samples'][0]
    sample2['cimac_sample_id'] = 'new_id_1'

    ct5 = merger.merge(ct3, ct4)
    assert len(ct5['participants'][0]['samples']) == 2

    # now lets add a new aliquot to one of the samples.
    ct6 = copy.deepcopy(ct5)
    aliquot2 = ct6['participants'][0]['samples'][0]['aliquots'][0]
    aliquot2['cimac_aliquot_id'] = 'new_ali_id_1'

    ct7 = merger.merge(ct5, ct6)
    assert len(ct7['participants'][0]['samples'][0]['aliquots']) == 2


MINIMAL_CT_1PA1SA1AL = {
    "lead_organization_study_id": "minimal",
    "participants": [
        {
            "samples": [
                {
                    "aliquots": [
                        {
                            "cimac_aliquot_id": "Aliquot 1",
                            "units": "Other",
                            "material_used": 1,
                            "material_remaining": 0,
                            "aliquot_quality_status": "Other",
                            "aliquot_replacement": "N/A",
                            "aliquot_status": "Other"
                        }
                    ],
                    "genomic_source": "Tumor",
                    "time_point": "---",
                    "sample_location": "---",
                    "specimen_type": "Other",
                    "specimen_format": "Other",
                    "site_sample_id": "site Sample 1",
                    "cimac_sample_id": "Sample 1"
                }
            ],
            "cimac_participant_id": "Patient 1",
            "trial_participant_id": "trial Patient 1",
            "cohort_id": "---",
            "arm_id": "---"
        }
    ]
}
def test_samples_merge():

    # one with 1 sample
    a1 = copy.deepcopy(MINIMAL_CT_1PA1SA1AL)
    
    # create a2 and modify ids to trigger merge behavior
    a2 = copy.deepcopy(a1)
    a2['participants'][0]['samples'][0]['cimac_sample_id'] = "something different"

    # create validator assert schema is valid.
    validator = load_and_validate_schema("clinical_trial.json", return_validator=True)
    schema = validator.schema

    # merge them
    merger = Merger(schema)
    a3 = merger.merge(a1, a2)
    assert len(a3['participants']) == 1
    assert len(a3['participants'][0]['samples']) == 2


@pytest.mark.parametrize('schema_path, xlsx_path', template_paths())
def test_prism(schema_path, xlsx_path):

    # create validators
    validator = load_and_validate_schema("clinical_trial.json", return_validator=True)
    schema = validator.schema

    # extract hint.
    hint = schema_path.split("/")[-1].replace("_template.json", "")

    # TODO: only implemented WES parsing...
    if hint != "wes":
        return

    # turn into object.
    ct, file_maps = prismify(xlsx_path, schema_path, assay_hint=hint)

    assert len(ct['assays'][hint]) == 1
    
    # we merge it with a preexisting one
    # 1. we get all 'required' fields from this preexisting
    # 2. we can check it didn't overwrite anything crucial
    merger = Merger(schema)
    merged = merger.merge(MINIMAL_CT_1PA1SA1AL, ct)

    # assert works
    validator.validate(merged)

    if hint == 'wes':
        assert merged["lead_organization_study_id"] == "10021"
    else:
        assert MINIMAL_CT_1PA1SA1AL["lead_organization_study_id"] == merged["lead_organization_study_id"]


@pytest.mark.parametrize('schema_path, xlsx_path', template_paths())
def test_filepath_gen_wes_only(schema_path, xlsx_path):
    # extract hint.
    hint = schema_path.split("/")[-1].replace("_template.json", "")

    # TODO: only implemented WES parsing...
    if hint != "wes":
        return

    # create validators
    validator = load_and_validate_schema("clinical_trial.json", return_validator=True)
    schema = validator.schema

    # parse the spreadsheet and get the file maps
    _, file_maps = prismify(xlsx_path, schema_path, assay_hint=hint)
    # we ignore and do not validate 'ct' 
    # because it's only a ct patch not a full ct 

    # assert we have the right counts.
    if hint == "wes":

        # check the number of files present.
        assert len(file_maps) == 6

        # we should have 2 fastq per sample.
        # we should have 2 tot forward.
        assert 2 == sum([1 for x in file_maps if "/fastq_1/" in x['gs_key']])
        # we should have 2 tot rev.
        assert 2 == sum([1 for x in file_maps if "/fastq_2/" in x['gs_key']])
        # in total local
        assert 4 == sum([1 for x in file_maps if x['local_path'].endswith(".fastq")])

        # we should have 2 text files
        assert 2 == sum([1 for x in file_maps if "/read_group_mapping_file/" in x['gs_key']])
        assert 2 == sum([1 for x in file_maps if x['local_path'].endswith(".txt")])

        # 2 participants
        assert 2 == len(set([x['gs_key'].split("/")[0] for x in file_maps]))
        # 2 samples
        assert 2 == len(set([x['gs_key'].split("/")[1] for x in file_maps]))
        # 2 aliquots
        assert 2 == len(set([x['gs_key'].split("/")[2] for x in file_maps]))




def test_prismify_wes_only():

    # create validators
    validator = load_and_validate_schema("clinical_trial.json", return_validator=True)
    schema = validator.schema

    # create the example template.
    temp_path = os.path.join(SCHEMA_DIR, 'templates', 'metadata', 'wes_template.json')
    xlsx_path = os.path.join(TEMPLATE_EXAMPLES_DIR, "wes_template.xlsx")
    hint = 'wes'

    # parse the spreadsheet and get the file maps
    ct, file_maps = prismify(xlsx_path, temp_path, assay_hint=hint)

    # we merge it with a preexisting one
    # 1. we get all 'required' fields from this preexisting
    # 2. we can check it didn't overwrite anything crucial
    merger = Merger(schema)
    merged = merger.merge(MINIMAL_CT_1PA1SA1AL, ct)

    # assert works
    validator.validate(merged)



def test_merge_artifact_wes_only():

    # create the clinical trial.
    ct = copy.deepcopy(WES_TEMPLATE_EXAMPLE_CT)


    # create validator
    validator = load_and_validate_schema("clinical_trial.json", return_validator=True)

    validator.validate(ct)

    # loop over each url
    searched_urls = []
    for i, url in enumerate(WES_TEMPLATE_EXAMPLE_GS_URLS):

        # attempt to merge
        ct, _ = merge_artifact(
                ct,
                object_url=url,
                assay_type="wes",
                file_size_bytes=i,
                uploaded_timestamp="01/01/2001",
                md5_hash=f"hash_{i}"
            )

        # assert we still have a good clinical trial object.
        validator.validate(ct)

        # search for this url and all previous (no clobber)
        searched_urls.append(url)

    for url in searched_urls:
        assert len((ct | grep(url))['matched_values']) > 0

    assert len(ct['assays']['wes']) == 1, "Multiple WESes created instead of merging into one"
    assert len(ct['assays']['wes'][0]['records']) == 2, "More records than expected"

    dd = DeepDiff(WES_TEMPLATE_EXAMPLE_CT,ct)

    # we add 6 required fields per artifact thus `*6`
    assert len(dd['dictionary_item_added']) == len(WES_TEMPLATE_EXAMPLE_GS_URLS)*6, "Unexpected CT changes"

    # in the process upload_placeholder gets removed per artifact
    assert len(dd['dictionary_item_removed']) == len(WES_TEMPLATE_EXAMPLE_GS_URLS), "Unexpected CT changes"
    assert list(dd.keys()) == ['dictionary_item_added', 'dictionary_item_removed'], "Unexpected CT changes"


def test_merge_ct_meta():
    """ 
    tests merging of two clinical trial metadata
    objects. Currently this test only supports
    WES but other tests should be added in the
    future
    """

    # create two clinical trials
    ct1 = copy.deepcopy(WES_TEMPLATE_EXAMPLE_CT)
    ct2 = copy.deepcopy(WES_TEMPLATE_EXAMPLE_CT)

    # first test the fact that base doc must be valid
    del ct2['participants']
    with pytest.raises(InvalidTargetException):
        merge_clinical_trial_metadata(ct1, ct2)

    with pytest.raises(InvalidTargetException):
        merge_clinical_trial_metadata(ct1, {})

    # next assert the merge is only happening on the same trial
    ct1["lead_organization_study_id"] = "not_the_same"
    ct2 = copy.deepcopy(WES_TEMPLATE_EXAMPLE_CT)
    with pytest.raises(RuntimeError):
        merge_clinical_trial_metadata(ct1, ct2)

    # revert the data to same key trial id but
    # include data in 1 that is missing in the other
    # at the trial level and assert the merge
    # does not clobber any
    ct1["lead_organization_study_id"] = ct2["lead_organization_study_id"] 
    ct1['trial_name'] = 'name ABC'
    ct2['nci_id'] = 'xyz1234'

    ct_merge = merge_clinical_trial_metadata(ct1, ct2)
    assert ct_merge['trial_name'] == 'name ABC'
    assert ct_merge['nci_id'] == 'xyz1234'

    # assert the patch over-writes the original value
    # when value is present in both objects
    ct1['trial_name'] = 'name ABC'
    ct2['trial_name'] = 'CBA eman'

    ct_merge = merge_clinical_trial_metadata(ct1, ct2)
    assert ct_merge['trial_name'] == 'name ABC'

    # now change the participant ids
    # this should cause the merge to have two
    # participants.
    ct1['participants'][0]['cimac_participant_id'] = 'different_id'

    ct_merge = merge_clinical_trial_metadata(ct1, ct2)
    assert len(ct_merge['participants']) == 1+len(WES_TEMPLATE_EXAMPLE_CT['participants'])

    # now lets have the same participant but adding multiple samples.
    ct1["lead_organization_study_id"] = ct2["lead_organization_study_id"] 
    ct1['participants'][0]['cimac_participant_id'] = \
        ct2['participants'][0]['cimac_participant_id']
    ct1['participants'][0]['samples'][0]['cimac_sample_id'] = 'new_id_1'
    ct1['participants'][1]['samples'][0]['cimac_sample_id'] = 'new_id_2'
 
    ct_merge = merge_clinical_trial_metadata(ct1, ct2)
    assert len(ct_merge['participants']) == len(WES_TEMPLATE_EXAMPLE_CT['participants'])
    assert sum(len(p['samples']) for p in ct_merge['participants']) == 2+sum(len(p['samples']) for p in WES_TEMPLATE_EXAMPLE_CT['participants'])


@pytest.mark.parametrize('schema_path, xlsx_path', template_paths())
def test_end_to_end_wes_olink(schema_path, xlsx_path):
    # extract hint
    hint = schema_path.split("/")[-1].replace("_template.json", "")

    # TODO: implement other assays
    if hint not in ["wes", "olink"]:
        return 

    # create validators
    validator = load_and_validate_schema("clinical_trial.json", return_validator=True)
    
    # parse the spreadsheet and get the file maps
    prism_patch, file_maps = prismify(xlsx_path, schema_path, assay_hint=hint)

    if hint != 'olink':
        assert len(prism_patch['assays'][hint]) == 1
        assert len(prism_patch['assays'][hint][0]['records']) == 2
    else:
        assert len(prism_patch['assays'][hint]['records']) == 2

    for f in file_maps:
        assert f'{hint}/' in f['gs_key'], f"No {hint} hint found"

    # assert we still have a good clinical trial object, so we can save it
    # but we need to merge it, because "prismify" provides only a patch
    full_after_prism = merge_clinical_trial_metadata(prism_patch, WES_TEMPLATE_EXAMPLE_CT)
    validator.validate(full_after_prism)

    patch_copy_4_artifacts = copy.deepcopy(prism_patch)

    #now we simulate that upload was successful 
    searched_urls = []
    for i, fmap_entry in enumerate(file_maps):

        # attempt to merge
        patch_copy_4_artifacts, _ = merge_artifact(
                patch_copy_4_artifacts,
                object_url=fmap_entry['gs_key'],
                assay_type=hint,
                file_size_bytes=i,
                uploaded_timestamp="01/01/2001",
                md5_hash=f"hash_{i}"
            )

        # assert we still have a good clinical trial object, so we can save it
        validator.validate(merge_clinical_trial_metadata(patch_copy_4_artifacts, WES_TEMPLATE_EXAMPLE_CT))

        # we will than search for this url in the resulting ct, 
        # to check all artifacts were indeed merged
        searched_urls.append(fmap_entry['gs_key'])

    # `merge_artifact` modifies ct in-place, so 
    full_ct = merge_clinical_trial_metadata(patch_copy_4_artifacts, WES_TEMPLATE_EXAMPLE_CT)

    if hint == 'wes':
        assert len(searched_urls) == 3*2 # 3 files per entry in xlsx

        stripped_uuid_urls = [u[:-len("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")] for u in searched_urls]
        stripped_uuid_WES = [u[:-len("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")] for u in WES_TEMPLATE_EXAMPLE_GS_URLS]
        assert stripped_uuid_urls == stripped_uuid_WES

    for url in searched_urls:
        assert len((full_ct | grep(url))['matched_values']) == 1 # each gs_url only once  

    # olink is special - it's not an array
    if hint == "olink":
        assert len(full_ct['assays'][hint]['records']) == 2, "More records than expected"
    else:
        assert len(full_ct['assays'][hint]) == 1+len(WES_TEMPLATE_EXAMPLE_CT['assays'][hint]), f"Multiple {hint}-assays created instead of merging into one"
        assert len(full_ct['assays'][hint][0]['records']) == 2, "More records than expected"

    dd = DeepDiff(full_after_prism, full_ct)

    if hint=='wes':
        # 6 files * 6 artifact atributes
        assert len(dd['dictionary_item_added']) == 6*6, "Unexpected CT changes"

        # in the process upload_placeholder gets removed per artifact = 6
        assert len(dd['dictionary_item_removed']) == len(searched_urls), "Unexpected CT changes"

        # nothing else in diff
        assert list(dd.keys()) == ['dictionary_item_added', 'dictionary_item_removed'], "Unexpected CT changes"

    elif hint == "olink":
        assert list(dd.keys()) == ['dictionary_item_added'], "Unexpected CT changes"

        # 6 artifact atributes * 5 files (2 per record + 1 study)
        assert len(dd['dictionary_item_added']) == 6*(2*2+1), "Unexpected CT changes"

    else:
        assert list(dd.keys()) == ['dictionary_item_added'], "Unexpected CT changes"
