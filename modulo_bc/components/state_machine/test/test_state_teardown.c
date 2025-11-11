#include "unity.h"
#include "state_machine/fsm.h"
#include "auth.h"
#include "tftp.h"

#include <string.h>

TEST_CASE("state_teardown_reset_globals limpa variaveis globais", "[state_machine]")
{
    memset(&lur_file, 0xAA, sizeof(lur_file));
    memset(hash, 0xBB, sizeof(hash));
    memset(&req, 0xCC, sizeof(req));

    req.opcode = 0xABCD;

    static char dummy_name[] = "dummy";
    filename = dummy_name;
    opcode = 123;
    n = 456;
    upload_failure_count = 7;

    auth_set_authenticated_for_test(true);
    TEST_ASSERT_TRUE(auth_is_authenticated());

    state_teardown_reset_globals();

    lur_data_t expected_lur = {0};
    tftp_packet_t expected_req = {0};
    uint8_t expected_hash[sizeof(hash)] = {0};

    TEST_ASSERT_EQUAL_MEMORY(&expected_lur, &lur_file, sizeof(lur_file));
    TEST_ASSERT_EQUAL_UINT8_ARRAY(expected_hash, hash, sizeof(hash));
    TEST_ASSERT_EQUAL_MEMORY(&expected_req, &req, sizeof(req));

    TEST_ASSERT_NULL(filename);
    TEST_ASSERT_EQUAL(0, opcode);
    TEST_ASSERT_EQUAL_INT32(0, n);
    TEST_ASSERT_EQUAL_UINT8(0, upload_failure_count);
    TEST_ASSERT_FALSE(auth_is_authenticated());
}
