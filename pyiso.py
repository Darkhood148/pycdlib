import struct
import time

# There are a number of specific ways that numerical data is stored in the
# ISO9660/Ecma-119 standard.  In the text these are reference by the section
# number they are stored in.  A brief synopsis:
#
# 7.1.1 - 8-bit number
# 7.2.3 - 16-bit number, stored first as little-endian then as big-endian (4 bytes total)
# 7.3.1 - 32-bit number, stored as little-endian
# 7.3.2 - 32-bit number ,stored as big-endian
# 7.3.3 - 32-bit number, stored first as little-endian then as big-endian (8 bytes total)

VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD = 0
VOLUME_DESCRIPTOR_TYPE_PRIMARY = 1
VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY = 2
VOLUME_DESCRIPTOR_TYPE_VOLUME_PARTITION = 3
VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR = 255

class Iso9660Date(object):
    # Ecma-119, 8.4.26.1 specifies the date format as: 20150424121822110xf0 (offset from GMT in 15min intervals, -16 for us)
    def __init__(self, datestr):
        self.year = 0
        self.month = 0
        self.dayofmonth = 0
        self.hour = 0
        self.minute = 0
        self.second = 0
        self.hundredthsofsecond = 0
        self.gmtoffset = 0
        self.present = False
        if len(datestr) != 17:
            raise Exception("Invalid ISO9660 date string")
        if datestr[:-1] == '0'*16 and datestr[-1] == '\x00':
            # if the string was all zero, it means it wasn't specified; this
            # is valid, but we can't do any further work, so just bail out of
            # here
            return
        self.present = True
        timestruct = time.strptime(datestr[:-3], "%Y%m%d%H%M%S")
        self.year = timestruct.tm_year
        self.month = timestruct.tm_mon
        self.dayofmonth = timestruct.tm_mday
        self.hour = timestruct.tm_hour
        self.minute = timestruct.tm_min
        self.second = timestruct.tm_sec
        self.hundredthsofsecond = int(datestr[14:15])
        self.gmtoffset = struct.unpack("=B", datestr[16])

    def __str__(self):
        if self.present:
            return "%.4d/%.2d/%.2d %.2d:%.2d:%.2d.%.2d" % (self.year,
                                                           self.month,
                                                           self.dayofmonth,
                                                           self.hour,
                                                           self.minute,
                                                           self.second,
                                                           self.hundredthsofsecond)
        else:
            return "N/A"

class FileOrTextIdentifier(object):
    def __init__(self, ident_str):
        self.text = ident_str
        # According to Ecma-119, 8.4.20, 8.4.21, and 8.4.22, if the first
        # byte is a 0x5f, then the rest of the field specifies a filename.
        # It is not specified, but presumably if it is not a filename, then it
        # is an arbitrary text string.
        self.is_file = False
        if ident_str[0] == "\x5f":
            # If it is a file, Ecma-119 says that it must be at the Root
            # directory and it must be 8.3 (so 12 byte, plus one for the 0x5f)
            if len(ident_str) > 13:
                raise Exception("Filename for identifier is not in 8.3 format!")
            self.is_file = True
            self.text = ident_str[1:]

    def isfile(self):
        return self.is_file

    def istext(self):
        return not self.is_file

    def __str__(self):
        fileortext = "Text"
        if self.is_file:
            fileortext = "File"
        return "%s (%s)" % (self.text, fileortext)

class PrimaryVolumeDescriptor(object):
    def __init__(self, vd):
        # Ecma-119 says that the Volume Descriptor set is a sequence of volume
        # descriptors recorded in consecutively numbered Logical Sectors
        # starting with Logical Sector Number 16.  Since sectors are 2048 bytes
        # in length, we start at sector 16 * 2048
        fmt = "=B5sBB32s32sQLLQQQQHHHHHHLLLLLL34s128s128s128s128s37s37s37s17s17s17s17sBB512s653s"
        (self.descriptor_type, self.identifier, self.version, unused1,
         self.system_identifier, self.volume_identifier, unused2,
         self.space_size_le, self.space_size_be, unused3dot1, unused3dot2,
         unused3dot3, unused3dot4, self.set_size_le, self.set_size_be,
         self.seqnum_le, self.seqnum_be, self.logical_block_size_le,
         self.logical_block_size_be, self.path_table_size_le,
         self.path_table_size_be, self.path_table_location_le,
         self.optional_path_table_location_le, self.path_table_location_be,
         self.optional_path_table_location_be, root_dir_record,
         self.volume_set_identifier, pub_ident_str, prepare_ident_str,
         app_ident_str, self.copyright_file_identifier,
         self.abstract_file_identifier, self.bibliographic_file_identifier,
         vol_create_date_str, vol_mod_date_str, vol_expire_date_str,
         vol_effective_date_str, self.file_structure_version, unused4,
         self.application_use, unused5) = struct.unpack(fmt, vd)

        # According to Ecma-119, 8.4.1, the primary volume descriptor type
        # should be 1
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_PRIMARY:
            raise Exception("Invalid primary volume descriptor")
        # According to Ecma-119, 8.4.2, the identifier should be "CD001"
        if self.identifier != "CD001":
            raise Exception("invalid CD isoIdentification")
        # According to Ecma-119, 8.4.3, the version should be 1
        if self.version != 1:
            raise Exception("Invalid primary volume descriptor version")
        # According to Ecma-119, 8.4.4, the first unused field should be 0
        if unused1 != 0:
            raise Exception("data in unused field not zero")
        # According to Ecma-119, 8.4.5, the second unused field (after the
        # system identifier and volume identifier) should be 0
        if unused2 != 0:
            raise Exception("data in 2nd unused field not zero")
        # According to Ecma-119, 8.4.9, the third unused field should be all 0
        if unused3dot1 != 0 or unused3dot2 != 0 or unused3dot3 != 0 or unused3dot4 != 0:
            raise Exception("data in 3rd unused field not zero")
        if self.file_structure_version != 1:
            raise Exception("File structure version expected to be 1")
        if unused4 != 0:
            raise Exception("data in 4th unused field not zero")
        if unused5 != '\x00'*653:
            raise Exception("data in 5th unused field not zero")

        self.publisher_identifier = FileOrTextIdentifier(pub_ident_str)
        self.preparer_identifier = FileOrTextIdentifier(prepare_ident_str)
        self.application_identifier = FileOrTextIdentifier(app_ident_str)
        self.volume_creation_date = Iso9660Date(vol_create_date_str)
        self.volume_modification_date = Iso9660Date(vol_mod_date_str)
        self.volume_expiration_date = Iso9660Date(vol_expire_date_str)
        self.volume_effective_date = Iso9660Date(vol_effective_date_str)

        # FIXME: the root directory record needs to be implemented correctly;
        # right now we just have it as a 34-byte string placeholder.

    def __str__(self):
        retstr  = "Desc:                          %d\n" % self.descriptor_type
        retstr += "Identifier:                    '%s'\n" % self.identifier
        retstr += "Version:                       %d\n" % self.version
        retstr += "System Identifier:             '%s'\n" % self.system_identifier
        retstr += "Volume Identifier:             '%s'\n" % self.volume_identifier
        retstr += "Space Size:                    %d\n" % self.space_size_le
        retstr += "Set Size:                      %d\n" % self.set_size_le
        retstr += "SeqNum:                        %d\n" % self.seqnum_le
        retstr += "Logical Block Size:            %d\n" % self.logical_block_size_le
        retstr += "Path Table Size:               %d\n" % self.path_table_size_le
        retstr += "Path Table Location:           %d\n" % self.path_table_location_le
        retstr += "Optional Path Table Location:  %d\n" % self.optional_path_table_location_le
        retstr += "Volume Set Identifier:         '%s'\n" % self.volume_set_identifier
        retstr += "Publisher Identifier:          '%s'\n" % self.publisher_identifier
        retstr += "Preparer Identifier:           '%s'\n" % self.preparer_identifier
        retstr += "Application Identifier:        '%s'\n" % self.application_identifier
        retstr += "Copyright File Identifier:     '%s'\n" % self.copyright_file_identifier
        retstr += "Abstract File Identifier:      '%s'\n" % self.abstract_file_identifier
        retstr += "Bibliographic File Identifier: '%s'\n" % self.bibliographic_file_identifier
        retstr += "Volume Creation Date:          '%s'\n" % self.volume_creation_date
        retstr += "Volume Modification Date:      '%s'\n" % self.volume_modification_date
        retstr += "Volume Expiration Date:        '%s'\n" % self.volume_expiration_date
        retstr += "Volume Effective Date:         '%s'\n" % self.volume_effective_date
        retstr += "File Structure Version:        %d\n" % self.file_structure_version
        retstr += "Application Use:               '%s'" % self.application_use
        return retstr

class VolumeDescriptorSetTerminator(object):
    def __init__(self, vd):
        (self.descriptor_type, self.identifier, self.version, unused) = struct.unpack("=B5sB2041s", vd)

        # According to Ecma-119, 8.3.1, the volume descriptor set terminator
        # type should be 255
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR:
            raise Exception("Invalid descriptor type")
        # According to Ecma-119, 8.3.2, the identifier should be "CD001"
        if self.identifier != 'CD001':
            raise Exception("Invalid identifier")
        # According to Ecma-119, 8.3.3, the version should be 1
        if self.version != 1:
            raise Exception("Invalid version")
        # According to Ecma-119, 8.3.4, the rest of the terminator should be 0
        if unused != '\x00'*2041:
            raise Exception("Invalid unused field")

class BootRecord(object):
    def __init__(self, vd):
        (self.descriptor_type, self.identifier, self.version,
         self.boot_system_identifier, self.boot_identifier,
         self.boot_system_use) = struct.unpack("=B5sB32s32s1977s", vd)

        # According to Ecma-119, 8.2.1, the boot record type should be 0
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD:
            raise Exception("Invalid descriptor type")
        # According to Ecma-119, 8.2.2, the identifier should be "CD001"
        if self.identifier != 'CD001':
            raise Exception("Invalid identifier")
        # According to Ecma-119, 8.2.3, the version should be 1
        if self.version != 1:
            raise Exception("Invalid version")

    def __str__(self):
        retstr  = "Desc:                          %d\n" % self.descriptor_type
        retstr += "Identifier:                    '%s'\n" % self.identifier
        retstr += "Version:                       %d\n" % self.version
        retstr += "Boot System Identifier:        '%s'\n" % self.boot_system_identifier
        retstr += "Boot Identifier:               '%s'\n" % self.boot_identifier
        retstr += "Boot System Use:               '%s'\n" % self.boot_system_use
        return retstr

class SupplementaryVolumeDescriptor(object):
    def __init__(self, vd):
        fmt = "=B5sBB32s32sQLL32sHHHHHHLLLLLL34s128s128s128s128s37s37s37s17s17s17s17sBB512s653s"
        (self.descriptor_type, self.identifier, self.version, self.flags,
         self.system_identifier, self.volume_identifier, unused2,
         self.space_size_le, self.space_size_be, self.escape_sequences,
         self.set_size_le, self.set_size_be, self.seqnum_le, self.seqnum_be,
         self.logical_block_size_le, self.logical_block_size_be,
         self.path_table_size_le, self.path_table_size_be,
         self.path_table_location_le, self.optional_path_table_location_le,
         self.path_table_location_be, self.optional_path_table_location_be,
         root_dir_record, self.volume_set_identifier, pub_ident_str,
         prepare_ident_str, app_ident_str, self.copyright_file_identifier,
         self.abstract_file_identifier, self.bibliographic_file_identifier,
         vol_create_date_str, vol_mod_date_str, vol_expire_date_str,
         vol_effective_date_str, self.file_structure_version, unused4,
         self.application_use, unused5) = struct.unpack(fmt, vd)

        # According to Ecma-119, 8.5.1, the primary volume descriptor type
        # should be 2
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY:
            raise Exception("Invalid primary volume descriptor")
        # According to Ecma-119, 8.4.2, the identifier should be "CD001"
        if self.identifier != "CD001":
            raise Exception("invalid CD isoIdentification")
        # According to Ecma-119, 8.5.2, the version should be 1
        if self.version != 1:
            raise Exception("Invalid primary volume descriptor version")
        # According to Ecma-119, 8.4.5, the second unused field (after the
        # system identifier and volume identifier) should be 0
        if unused2 != 0:
            raise Exception("data in 2nd unused field not zero")
        if self.file_structure_version != 1:
            raise Exception("File structure version expected to be 1")
        if unused4 != 0:
            raise Exception("data in 4th unused field not zero")
        if unused5 != '\x00'*653:
            raise Exception("data in 5th unused field not zero")

        self.publisher_identifier = FileOrTextIdentifier(pub_ident_str)
        self.preparer_identifier = FileOrTextIdentifier(prepare_ident_str)
        self.application_identifier = FileOrTextIdentifier(app_ident_str)
        self.volume_creation_date = Iso9660Date(vol_create_date_str)
        self.volume_modification_date = Iso9660Date(vol_mod_date_str)
        self.volume_expiration_date = Iso9660Date(vol_expire_date_str)
        self.volume_effective_date = Iso9660Date(vol_effective_date_str)

        # FIXME: the root directory record needs to be implemented correctly;
        # right now we just have it as a 34-byte string placeholder.

    def __str__(self):
        retstr  = "Desc:                          %d\n" % self.descriptor_type
        retstr += "Identifier:                    '%s'\n" % self.identifier
        retstr += "Version:                       %d\n" % self.version
        retstr += "Flags:                         %d\n" % self.flags
        retstr += "System Identifier:             '%s'\n" % self.system_identifier
        retstr += "Volume Identifier:             '%s'\n" % self.volume_identifier
        retstr += "Space Size:                    %d\n" % self.space_size_le
        retstr += "Escape Sequences:              '%s'\n" % self.escape_sequences
        retstr += "Set Size:                      %d\n" % self.set_size_le
        retstr += "SeqNum:                        %d\n" % self.seqnum_le
        retstr += "Logical Block Size:            %d\n" % self.logical_block_size_le
        retstr += "Path Table Size:               %d\n" % self.path_table_size_le
        retstr += "Path Table Location:           %d\n" % self.path_table_location_le
        retstr += "Optional Path Table Location:  %d\n" % self.optional_path_table_location_le
        retstr += "Volume Set Identifier:         '%s'\n" % self.volume_set_identifier
        retstr += "Publisher Identifier:          '%s'\n" % self.publisher_identifier
        retstr += "Preparer Identifier:           '%s'\n" % self.preparer_identifier
        retstr += "Application Identifier:        '%s'\n" % self.application_identifier
        retstr += "Copyright File Identifier:     '%s'\n" % self.copyright_file_identifier
        retstr += "Abstract File Identifier:      '%s'\n" % self.abstract_file_identifier
        retstr += "Bibliographic File Identifier: '%s'\n" % self.bibliographic_file_identifier
        retstr += "Volume Creation Date:          '%s'\n" % self.volume_creation_date
        retstr += "Volume Modification Date:      '%s'\n" % self.volume_modification_date
        retstr += "Volume Expiration Date:        '%s'\n" % self.volume_expiration_date
        retstr += "Volume Effective Date:         '%s'\n" % self.volume_effective_date
        retstr += "File Structure Version:        %d\n" % self.file_structure_version
        retstr += "Application Use:               '%s'" % self.application_use
        return retstr

class VolumePartition(object):
    def __init__(self, vd):
        (self.descriptor_type, self.identifier, self.version, unused,
         self.system_identifier, self.volume_partition_identifier,
         self.volume_partition_location_le, self.volume_partition_location_be,
         self.volume_partition_size_le, self.volume_partition_size_be,
         self.system_use) = struct.unpack("=B5sBB32s32sLLLL1960s", vd)

        # According to Ecma-119, 8.6.1, the volume partition type should be 3
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_VOLUME_PARTITION:
            raise Exception("Invalid descriptor type")
        # According to Ecma-119, 8.6.2, the identifier should be "CD001"
        if self.identifier != 'CD001':
            raise Exception("Invalid identifier")
        # According to Ecma-119, 8.6.3, the version should be 1
        if self.version != 1:
            raise Exception("Invalid version")
        # According to Ecma-119, 8.6.4, the unused field should be 0
        if unused != 0:
            raise Exception("Unused field should be zero")

    def __str__(self):
        retstr  = "Desc:                          %d\n" % self.descriptor_type
        retstr += "Identifier:                    '%s'\n" % self.identifier
        retstr += "Version:                       %d\n" % self.version
        retstr += "System Identifier:             '%s'\n" % self.system_identifier
        retstr += "Volume Partition Identifier:   '%s'\n" % self.volume_partition_identifier
        retstr += "Volume Partition Location:     %d\n" % self.volume_partition_location_le
        retstr += "Volume Partition Size:         %d\n" % self.volume_partition_size_le
        retstr += "System Use:                    '%s'" % self.system_use
        return retstr

class PyIso(object):
    def _parse_volume_descriptors(self, cdfd):
        # Ecma-119 says that the Volume Descriptor set is a sequence of volume
        # descriptors recorded in consecutively numbered Logical Sectors
        # starting with Logical Sector Number 16.  Since sectors are 2048 bytes
        # in length, we start at sector 16 * 2048
        pvds = []
        vdsts = []
        brs = []
        svds = []
        vpds = []
        cdfd.seek(16*2048)
        done = False
        while not done:
            vd = cdfd.read(2048)
            (desc_type,) = struct.unpack("=B", vd[0])
            if desc_type == VOLUME_DESCRIPTOR_TYPE_PRIMARY:
                pvds.append(PrimaryVolumeDescriptor(vd))
            elif desc_type == VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR:
                vdsts.append(VolumeDescriptorSetTerminator(vd))
                # Once we see a set terminator, we stop parsing.  Oddly,
                # Ecma-119 says there may be multiple set terminators, but in
                # that case I don't know how to tell when we are done parsing
                # volume descriptors.  Leave this for now.
                done = True
            elif desc_type == VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD:
                brs.append(BootRecord(vd))
            elif desc_type == VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY:
                svds.append(SupplementaryVolumeDescriptor(vd))
            elif desc_type == VOLUME_DESCRIPTOR_TYPE_VOLUME_PARTITION:
                vpds.append(VolumePartition(vd))
        return pvds, svds, vpds, brs, vdsts

    def __init__(self, filename):
        self.fd = open(filename, "r")
        # Get the Primary Volume Descriptor (pvd), the set of Supplementary
        # Volume Descriptors (svds), the set of Volume Partition
        # Descriptors (vpds), the set of Boot Records (brs), and the set of
        # Volume Descriptor Set Terminators (vdsts)
        pvds, self.svds, self.vpds, self.brs, self.vdsts = self._parse_volume_descriptors(self.fd)
        if len(pvds) != 1:
            raise Exception("Valid ISO9660 filesystems have one and only one Primary Volume Descriptors")
        if len(self.vdsts) < 1:
            raise Exception("Valid ISO9660 filesystems must have at least one Volume Descriptor Set Terminators")
        self.pvd = pvds[0]
        print(self.pvd)

    def close(self):
        self.fd.close()
