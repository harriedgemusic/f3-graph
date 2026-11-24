#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

typedef int (__stdcall *cbtype)(const char *what, int int1, int int2, const char *str);
typedef int (__cdecl *FreeArcExtractFn)(cbtype callback, ...);

static char last_file[1024] = "";
static int cb_ret = 0;

static int __stdcall progress_cb(const char *what, int int1, int int2, const char *str) {
    if (!what) return cb_ret;
    if (strcmp(what, "write") == 0 || strcmp(what, "read") == 0) {
        static int last_mb = -1;
        if (int1 != last_mb && (int1 % 20 == 0 || int1 < 5)) {
            last_mb = int1;
            printf("[%s] %d %d (%s)\n", what, int1, int2, last_file);
            fflush(stdout);
        }
    } else {
        if (strcmp(what, "filename") == 0 && str) {
            snprintf(last_file, sizeof(last_file), "%s", str);
        }
        printf("[CB] what=%s int1=%d int2=%d str=%s\n", what, int1, int2, str ? str : "(null)");
        fflush(stdout);
    }
    return cb_ret;
}

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "Usage: %s <cmd:x|l> <cbret:0|1> <archive> [outdir] [mask...]\n", argv[0]);
        return 2;
    }

    const char *cmd = argv[1];
    cb_ret = atoi(argv[2]);
    const char *archive = argv[3];
    const char *outdir = argc > 4 ? argv[4] : NULL;
    const char *m1 = argc > 5 ? argv[5] : NULL;
    const char *m2 = argc > 6 ? argv[6] : NULL;

    HMODULE hDll = LoadLibraryA("unarc.dll");
    if (!hDll) {
        fprintf(stderr, "Failed to load unarc.dll (err=%lu)\n", GetLastError());
        return 3;
    }

    FreeArcExtractFn fn = (FreeArcExtractFn)GetProcAddress(hDll, "FreeArcExtract");
    if (!fn) {
        fprintf(stderr, "Failed to resolve FreeArcExtract (err=%lu)\n", GetLastError());
        return 4;
    }

    int rc;
    if (outdir && outdir[0]) {
        char dp_arg[1024];
        snprintf(dp_arg, sizeof(dp_arg), "-dp%s", outdir);
        printf("Running cmd=%s cbret=%d arc=%s dp=%s m1=%s m2=%s\n", cmd, cb_ret, archive, dp_arg, m1 ? m1 : "(null)", m2 ? m2 : "(null)");
        fflush(stdout);
        rc = fn(progress_cb, cmd, "-o+", "-cfgarc.ini", dp_arg, "--", archive, m1, m2, NULL);
    } else {
        printf("Running cmd=%s cbret=%d arc=%s\n", cmd, cb_ret, archive);
        fflush(stdout);
        rc = fn(progress_cb, cmd, "-cfgarc.ini", "--", archive, m1, m2, NULL);
    }
    printf("FreeArcExtract returned: %d\n", rc);
    fflush(stdout);

    FreeLibrary(hDll);
    return rc;
}
