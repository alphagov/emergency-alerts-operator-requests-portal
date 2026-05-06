import glob
import json
import os
import sys
from xml.dom.minidom import Document, Node, parse


def main():
    if len(sys.argv) < 2:
        print("Usage: python report-test-results.py <test-report-dir>")
        sys.exit(1)

    test_dir = sys.argv[1]
    test_files = glob.glob(os.path.join(test_dir, "*"))
    print("Found test report files: " + ", ".join(test_files))

    failed_tests = aggregate_failures(test_files)

    if os.environ.get("ENVIRONMENT") == "preview":
        log_final_results(failed_tests)


def aggregate_failures(test_files: list[str]) -> list[str]:
    artefact_bucket = os.environ.get("FUNCTIONAL_TEST_ARTEFACT_BUCKET_NAME")
    failed_tests = []

    for test_file in test_files:
        test_results = extract_test_results(test_file, parse(test_file))
        for r in test_results:
            success = "PASS" if len(r) < 4 else "FAIL"
            result = f"MNO-FT-{r[0].upper()} | {success} | NAME: {r[1]} | TIME: {r[2]}"

            if len(r) > 3:
                result = f"{result} | ERROR: {r[3]} | FILE: {r[4]}"
                if artefact_bucket:
                    result = f"{result} | Artefact bucket: {artefact_bucket}"

            if success == "FAIL":
                failed_tests.append(f"- {r[1]}: {r[3]}\n")

            print(result.replace("\n", " "), sep="")

    return failed_tests


def log_final_results(failed_tests: list[str]):
    if len(failed_tests) > 3:
        overflow = len(failed_tests) - 3
        failed_tests = failed_tests[:3]
        failed_tests.append(f"- ...{overflow} more failed.")

    test_string = "".join(failed_tests)

    print(
        json.dumps(
            {
                "test_run_status": "FAILED" if failed_tests else "PASSED",
                "failures": test_string if test_string else None,
            },
            separators=(",", ":"),
        )
    )


def extract_test_results(test_group: str, document: Document) -> list:
    results = []
    for result in document.getElementsByTagName("testcase"):
        name = result.getAttribute("name")
        elapsed = result.getAttribute("time")

        failure = result.getElementsByTagName("failure")
        error = result.getElementsByTagName("error")

        test_failure = None
        if failure:
            test_failure = failure[0]
        elif error:
            test_failure = error[0]

        failure_message, failure_summary = _extract_failure_detail(test_failure)

        if failure_message is not None or failure_summary is not None:
            results.append((test_group, name, elapsed, failure_summary, failure_message))
        else:
            results.append((test_group, name, elapsed))

    return results


def _extract_failure_detail(failure):
    if failure is None:
        return (None, None)

    failure_message = failure.getAttribute("message") if failure.hasAttribute("message") else None
    failure_summary = None

    if failure.hasChildNodes():
        node = failure.firstChild
        if node and node.nodeType == Node.TEXT_NODE and node.nodeValue:
            lines = node.nodeValue.strip().split("\n")
            last_line = lines[-1].strip()
            parts = last_line.split(":")
            if len(parts) >= 2:
                failure_summary = f"{parts[0]}, line {parts[1]}"

    return (failure_summary, failure_message)


if __name__ == "__main__":
    main()
