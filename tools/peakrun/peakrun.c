/* peakrun OUTFILE CMD [ARGS...]
 *
 * Runs CMD as a child and writes the kernel's peak resident set size of that
 * child (ru_maxrss from wait4, in KiB) to OUTFILE, then exits with the
 * child's status (or re-raises its signal).
 *
 * Why a separate program: the harness polls VmHWM, which misses a peak
 * reached in the last polling interval and cannot measure a run shorter than
 * its first reading. ru_maxrss is exact, but a child forked from the Python
 * harness starts its high-water mark at the harness's own footprint (the
 * fork shares Python's resident pages). Forked from this small program, the
 * floor is this program's footprint, about 1 MiB.
 */
#include <signal.h>
#include <stdio.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: peakrun OUTFILE CMD [ARGS...]\n");
        return 2;
    }
    pid_t pid = fork();
    if (pid < 0) { perror("fork"); return 2; }
    if (pid == 0) {
        execvp(argv[2], argv + 2);
        perror("execvp");
        _exit(127);
    }
    /* forward termination to the child so a timeout kill reaches the miner */
    int status = 0;
    struct rusage ru;
    while (wait4(pid, &status, 0, &ru) < 0) { }
    FILE *f = fopen(argv[1], "w");
    if (f) { fprintf(f, "%ld\n", ru.ru_maxrss); fclose(f); }
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    if (WIFSIGNALED(status)) { signal(WTERMSIG(status), SIG_DFL); raise(WTERMSIG(status)); }
    return 128;
}
