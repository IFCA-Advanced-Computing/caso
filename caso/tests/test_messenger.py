# -*- coding: utf-8 -*-

# Copyright 2014 Spanish National Research Council (CSIC)
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Tests for messenger module."""

import caso.messenger
import caso.record


class TestFilterRecords:
    """Test cases for the _filter_records function."""

    def test_filter_records_returns_all_when_no_filter(
        self, cloud_record, ip_record, storage_record
    ):
        """Test that all records are returned when no filter is specified."""
        records = [cloud_record, ip_record, storage_record]
        result = caso.messenger._filter_records(records, None)
        assert result == records

    def test_filter_records_returns_all_when_empty_filter(
        self, cloud_record, ip_record, storage_record
    ):
        """Test that all records are returned when filter list is empty."""
        records = [cloud_record, ip_record, storage_record]
        result = caso.messenger._filter_records(records, [])
        assert result == records

    def test_filter_records_filters_by_cloud(
        self, cloud_record, ip_record, storage_record
    ):
        """Test filtering for cloud records only."""
        records = [cloud_record, ip_record, storage_record]
        result = caso.messenger._filter_records(records, ["cloud"])
        assert len(result) == 1
        assert isinstance(result[0], caso.record.CloudRecord)

    def test_filter_records_filters_by_ip(
        self, cloud_record, ip_record, storage_record
    ):
        """Test filtering for IP records only."""
        records = [cloud_record, ip_record, storage_record]
        result = caso.messenger._filter_records(records, ["ip"])
        assert len(result) == 1
        assert isinstance(result[0], caso.record.IPRecord)

    def test_filter_records_filters_by_storage(
        self, cloud_record, ip_record, storage_record
    ):
        """Test filtering for storage records only."""
        records = [cloud_record, ip_record, storage_record]
        result = caso.messenger._filter_records(records, ["storage"])
        assert len(result) == 1
        assert isinstance(result[0], caso.record.StorageRecord)

    def test_filter_records_filters_by_multiple_types(
        self, cloud_record, ip_record, storage_record
    ):
        """Test filtering for multiple record types."""
        records = [cloud_record, ip_record, storage_record]
        result = caso.messenger._filter_records(records, ["cloud", "ip"])
        assert len(result) == 2
        assert any(isinstance(r, caso.record.CloudRecord) for r in result)
        assert any(isinstance(r, caso.record.IPRecord) for r in result)

    def test_filter_records_handles_accelerator(self, accelerator_record):
        """Test filtering for accelerator records."""
        records = [accelerator_record]
        result = caso.messenger._filter_records(records, ["accelerator"])
        assert len(result) == 1
        assert isinstance(result[0], caso.record.AcceleratorRecord)

    def test_filter_records_handles_energy(self, energy_record):
        """Test filtering for energy records."""
        records = [energy_record]
        result = caso.messenger._filter_records(records, ["energy"])
        assert len(result) == 1
        assert isinstance(result[0], caso.record.EnergyRecord)

    def test_filter_records_returns_empty_when_no_match(self, cloud_record, ip_record):
        """Test that empty list is returned when no records match filter."""
        records = [cloud_record, ip_record]
        result = caso.messenger._filter_records(records, ["storage", "energy"])
        assert result == []

    def test_filter_records_ignores_invalid_types(self, cloud_record, ip_record):
        """Test that invalid record types are ignored in the filter."""
        records = [cloud_record, ip_record]
        result = caso.messenger._filter_records(records, ["invalid_type"])
        # When all filter types are invalid, return all records
        assert result == records

    def test_filter_records_mixed_valid_invalid_types(
        self, cloud_record, ip_record, storage_record
    ):
        """Test filtering with mix of valid and invalid types."""
        records = [cloud_record, ip_record, storage_record]
        result = caso.messenger._filter_records(records, ["cloud", "invalid_type"])
        assert len(result) == 1
        assert isinstance(result[0], caso.record.CloudRecord)


class TestGetMessengerOpts:
    """Test cases for the get_messenger_opts function."""

    def test_ssm_messenger_has_default_record_types(self):
        """Test that SSM messenger has default record types."""
        opts = caso.messenger.get_messenger_opts("ssm")
        assert len(opts) == 1
        opt = opts[0]
        assert opt.name == "record_types"
        assert opt.default == caso.messenger.DEFAULT_SSM_RECORD_TYPES

    def test_ssmv4_messenger_has_default_record_types(self):
        """Test that SSMv4 messenger has default record types."""
        opts = caso.messenger.get_messenger_opts("ssmv4")
        assert len(opts) == 1
        opt = opts[0]
        assert opt.name == "record_types"
        assert opt.default == caso.messenger.DEFAULT_SSM_RECORD_TYPES

    def test_noop_messenger_has_empty_default(self):
        """Test that noop messenger has empty default (all record types)."""
        opts = caso.messenger.get_messenger_opts("noop")
        assert len(opts) == 1
        opt = opts[0]
        assert opt.name == "record_types"
        assert opt.default == []

    def test_logstash_messenger_has_empty_default(self):
        """Test that logstash messenger has empty default (all record types)."""
        opts = caso.messenger.get_messenger_opts("logstash")
        assert len(opts) == 1
        opt = opts[0]
        assert opt.name == "record_types"
        assert opt.default == []


class TestDefaultSsmRecordTypes:
    """Test cases for default SSM record types."""

    def test_default_ssm_record_types_includes_cloud(self):
        """Test that default SSM record types includes cloud."""
        assert "cloud" in caso.messenger.DEFAULT_SSM_RECORD_TYPES

    def test_default_ssm_record_types_includes_ip(self):
        """Test that default SSM record types includes ip."""
        assert "ip" in caso.messenger.DEFAULT_SSM_RECORD_TYPES

    def test_default_ssm_record_types_includes_accelerator(self):
        """Test that default SSM record types includes accelerator."""
        assert "accelerator" in caso.messenger.DEFAULT_SSM_RECORD_TYPES

    def test_default_ssm_record_types_includes_storage(self):
        """Test that default SSM record types includes storage."""
        assert "storage" in caso.messenger.DEFAULT_SSM_RECORD_TYPES

    def test_default_ssm_record_types_excludes_energy(self):
        """Test that default SSM record types excludes energy."""
        assert "energy" not in caso.messenger.DEFAULT_SSM_RECORD_TYPES


class TestValidRecordTypes:
    """Test cases for VALID_RECORD_TYPES constant."""

    def test_valid_record_types_contains_all_types(self):
        """Test that VALID_RECORD_TYPES contains all expected types."""
        expected = {"cloud", "ip", "accelerator", "storage", "energy"}
        assert caso.messenger.VALID_RECORD_TYPES == expected

    def test_record_type_map_matches_valid_record_types(self):
        """Test that RECORD_TYPE_MAP keys match VALID_RECORD_TYPES."""
        assert (
            set(caso.messenger.RECORD_TYPE_MAP.keys())
            == caso.messenger.VALID_RECORD_TYPES
        )
