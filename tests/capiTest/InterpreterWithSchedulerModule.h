/* 
	*************************************************************************

	InterpreterWithSchedulerModule.h

	Author:    James Hawk
	Created:   April. 2024
	Project:   SchedulerCapiTest

	Description:   

	  PyTaskletObject python type definition

	(c) CCP 2024

	*************************************************************************
*/
#pragma once
#ifndef InterpreterWithSchedulerModule_H
#define InterpreterWithSchedulerModule_H

#include <gtest/gtest.h>
#include <Scheduler.h>

struct InterpreterWithSchedulerModule : public ::testing::Test
{
	void SetUp();

	void TearDown();

    PyTaskletObject* CreateTasklet();

    PyObject* m_schedulerModule;

    PyObject* m_mainModule;

    PyObject* m_mainScheduler;

    SchedulerCAPI* m_api;
};

#endif // InterpreterWithSchedulerModule_H