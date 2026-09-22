#include <string.h>

#include "parameters.h"
#include "Global.h"

CParameters goparameters;


void CParameters::SetResultName(char *szresult_name)
{
	snprintf(szgenerator_filename, MAX_FILENAME_LEN, "%s.txt", szresult_name);
	snprintf(sznegborder_filename, MAX_FILENAME_LEN, "%s.fbd", szresult_name);
}

