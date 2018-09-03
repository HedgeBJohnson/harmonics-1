#!/software/development/Build/Anaconda3-4.4.0/envs/python-3.6/bin/python -u
#SBATCH --output=dr.txt

#

#SBATCH --ntasks=1
#SBATCH --time=48:00:00
#SBATCH --nodes=1
#SBATCH --mem-per-cpu=20G


# MAIN SCRIPT SECTION
# Scipt imports

import os
import sys
print('*** Python interpreter version ***\n')
print(sys.version,'\n')
sys.path.append(os.getcwd())
import subprocess
import warnings
import os.path
import optimization_tools
import time

# Initiate Dispy Node Server on Compute Nodes

print('*** Joker Computational Node Allocation ***')

nodes = subprocess.check_output('echo $SLURM_JOB_NODELIST',shell=True)
nodes = nodes.decode('utf-8')
nodes = nodes[8:-2]
#nodes = [int(nodes[0]),int(nodes[-1])]

print('Joker', nodes, '\n')
print('*** Dispy Server Startup Messages ***')
os.system('srun dispynode.py --clean --daemon & &>/dev/null')
print('\n')


def compute(n):  # executed on nodes
    import time
    time.sleep(n)
    return n

def job_callback(job): # executed at the client
    global pending_jobs, jobs_cond
    if (job.status == dispy.DispyJob.Finished  # most usual case
        or job.status in (dispy.DispyJob.Terminated, dispy.DispyJob.Cancelled,
                          dispy.DispyJob.Abandoned)):
        # 'pending_jobs' is shared between two threads, so access it with
        # 'jobs_cond' (see below)
        jobs_cond.acquire()
        if job.id: # job may have finished before 'main' assigned id
            pending_jobs.pop(job.id)
            dispy.logger.info('job "%s" done with %s: %s', job.id, job.result, len(pending_jobs))
            if len(pending_jobs) <= lower_bound:
                jobs_cond.notify()
        jobs_cond.release()

if __name__ == '__main__':
    import dispy, threading, random

    # set lower and upper bounds as appropriate; assuming there are 30
    # processors in a cluster, bounds are set to 50 to 100
    lower_bound, upper_bound = 50, 100
    # use Condition variable to protect access to pending_jobs, as
    # 'job_callback' is executed in another thread
    jobs_cond = threading.Condition()
    cluster = dispy.JobCluster(compute, callback=job_callback)
    pending_jobs = {}
    # submit 1000 jobs
    i = 0
    while i <= 1000:
        i += 1
        job = cluster.submit(random.uniform(3, 7))
        jobs_cond.acquire()
        job.id = i
        # there is a chance the job may have finished and job_callback called by
        # this time, so put it in 'pending_jobs' only if job is pending
        if job.status == dispy.DispyJob.Created or job.status == dispy.DispyJob.Running:
            pending_jobs[i] = job
            # dispy.logger.info('job "%s" submitted: %s', i, len(pending_jobs))
            if len(pending_jobs) >= upper_bound:
                while len(pending_jobs) > lower_bound:
                    jobs_cond.wait()
        jobs_cond.release()

    cluster.wait()
    cluster.print_status()
    cluster.close()